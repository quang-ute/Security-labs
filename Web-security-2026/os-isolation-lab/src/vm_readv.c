/*
 * vm_readv.c — attack the *right way*: the process_vm_readv(2) syscall.
 *
 * process_vm_readv is the kernel's sanctioned, explicit interface for
 * reading another process's address space. Note carefully: it is subject
 * to the EXACT same ptrace permission model as /proc/<pid>/mem. The file
 * was never the problem -- the permission model is.
 *
 * Modes:
 *   ./vm_readv <pid> <secret>          # attack an existing victim
 *   ./vm_readv --child <secret>        # fork/exec our own target and read
 *                                      # our OWN child: allowed at scope=1
 *
 * Permission outcomes (default ptrace_scope=1):
 *   - same UID, target is NOT our child  -> EPERM
 *   - target IS our child (--child mode) -> works, no root needed
 *   - we are root (CAP_SYS_PTRACE)        -> works
 *   - ptrace_scope=0 (sysctl), same UID   -> works
 *
 * We scan the largest anonymous rw region (the victim's 1 MiB buffer) so
 * the address reported matches the one `target` printed at startup.
 *
 * Build:  gcc -O0 -g -Wall -Wextra -o vm_readv vm_readv.c
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <signal.h>
#include <sys/uio.h>
#include <sys/types.h>
#include <sys/wait.h>

#define MAX_REGION (8u << 20)

static long find_bytes(const char *hay, size_t hl,
                       const char *needle, size_t nl) {
    size_t i;
    if (nl == 0 || nl > hl) return -1;
    for (i = 0; i + nl <= hl; i++)
        if (memcmp(hay + i, needle, nl) == 0)
            return (long)i;
    return -1;
}

/* largest anonymous rw region of `pid`; fills *out_start / *out_len */
static int find_largest_anon_rw(pid_t pid, unsigned long *out_start,
                                unsigned long *out_len) {
    char maps_path[64];
    snprintf(maps_path, sizeof maps_path, "/proc/%d/maps", pid);
    FILE *m = fopen(maps_path, "r");
    if (!m) { perror("fopen(maps)"); return -1; }

    char line[512], perms[8], dev[32], path[256];
    unsigned long start = 0, end = 0, off = 0, inode = 0;
    unsigned long best_start = 0, best_len = 0;

    while (fgets(line, sizeof line, m)) {
        path[0] = 0;
        int nf = sscanf(line, "%lx-%lx %7s %lx %31s %lu %255s",
                        &start, &end, perms, &off, dev, &inode, path);
        if (nf < 6) continue;
        if (perms[0] != 'r' || perms[1] != 'w') continue;
        int anon = (nf == 6) || strcmp(path, "[heap]") == 0;
        if (!anon) continue;

        unsigned long len = end - start;
        if (len == 0 || len > MAX_REGION) continue;
        if (len > best_len) { best_start = start; best_len = len; }
    }
    fclose(m);
    if (best_len == 0) return -1;
    *out_start = best_start;
    *out_len   = best_len;
    return 0;
}

static int read_secret(pid_t pid, const char *secret, size_t secret_len,
                       unsigned long *out_addr) {
    unsigned long start = 0, len = 0;
    if (find_largest_anon_rw(pid, &start, &len) != 0) {
        fprintf(stderr, "[-] could not read /proc/%d/maps\n", pid);
        return -1;
    }

    char *buf = malloc(len);
    if (!buf) { perror("malloc"); return -1; }

    struct iovec local  = { buf, len };
    struct iovec remote = { (void *)start, len };
    ssize_t got = process_vm_readv(pid, &local, 1, &remote, 1, 0);
    if (got < 0) {
        int e = errno;
        if (e == EPERM) {              /* access denied --- the point */
            fprintf(stderr, "[-] process_vm_readv(pid=%d, 0x%lx, %lu bytes): "
                            "%s (errno=%d)\n", pid, start, len, strerror(e), e);
            fprintf(stderr,
                    "    => EPERM: same gate as /proc/%d/mem. Same UID is not\n"
                    "       enough under ptrace_scope=1 unless you are the\n"
                    "       target's parent (or root, or scope=0).\n", pid);
            free(buf);
            return -1;
        }
        fprintf(stderr, "[-] process_vm_readv: %s (errno=%d) — keep scanning…\n",
                strerror(e), e);
        free(buf);
        return -1;
    }

    long off = find_bytes(buf, (size_t)got, secret, secret_len);
    if (off >= 0) {
        *out_addr = start + (unsigned long)off;
        printf("[+] process_vm_readv: SECRET at 0x%lx\n", *out_addr);
        printf("    '%.32s'\n", buf + off);
        free(buf);
        return 0;
    }
    fprintf(stderr, "[-] secret not found in region.\n");
    free(buf);
    return -1;
}

int main(int argc, char **argv) {
    pid_t pid = 0;
    const char *secret;
    int child_mode = 0;

    if (argc >= 3 && strcmp(argv[1], "--child") == 0) {
        child_mode = 1;
        secret = argv[2];
    } else if (argc >= 3) {
        pid    = (pid_t)atoi(argv[1]);
        secret = argv[2];
    } else {
        fprintf(stderr, "usage: %s <pid> <secret> | %s --child <secret>\n",
                argv[0], argv[0]);
        return 2;
    }

    if (child_mode) {
        pid = fork();
        if (pid == 0) {
            execl("./target", "./target", secret, "60", (char *)NULL);
            perror("execl(target)");
            _exit(127);
        }
        sleep(1);   /* let the child park the secret (1 MiB mmap exists   */
                    /* immediately; page contents are established at exec) */
        printf("[*] reading OUR OWN CHILD pid=%d (parent allowed at scope=1)\n",
               pid);
    }

    unsigned long addr = 0;
    int rc = read_secret(pid, secret, strlen(secret), &addr);

    if (child_mode) { kill(pid, SIGTERM); waitpid(pid, NULL, 0); }
    return rc == 0 ? 0 : 1;
}