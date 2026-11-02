/*
 * vm_writev.c — stretch demo: WRITE into a live process's memory.
 *
 * process_vm_writev(2): the write-side twin of process_vm_readv, same
 * permission model. We locate the victim's secret (via vm_readv), then
 * overwrite it while the process is running; the victim's own stdout
 * shows the change a tick later. This is the crude mechanism underlying
 * game trainers / hot-patching / injection.
 *
 * Requires ptrace rights over the victim: root, or attacker-is-parent,
 * or ptrace_scope=0.
 *
 * Build:  gcc -O0 -g -Wall -Wextra -o vm_writev vm_writev.c
 * Run:    sudo ./vm_writev <pid> "SUPERSECRET-ROOT"
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/uio.h>

static long find_bytes(const char *hay, size_t hl,
                       const char *needle, size_t nl) {
    size_t i;
    if (nl == 0 || nl > hl) return -1;
    for (i = 0; i + nl <= hl; i++)
        if (memcmp(hay + i, needle, nl) == 0)
            return (long)i;
    return -1;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: %s <pid> <secret-to-flip>\n", argv[0]);
        return 2;
    }
    pid_t pid = (pid_t)atoi(argv[1]);
    const char *secret = argv[2];
    const char *replacement = "HACKED!!!-";   /* same length (10 chars) */
    size_t secret_len = strlen(secret);
    size_t repl_len   = strlen(replacement);
    if (repl_len > secret_len) {
        fprintf(stderr, "replacement longer than secret; pad it.\n");
        return 2;
    }

    /* locate the largest anonymous rw region (the 1 MiB buffer) */
    char maps_path[64];
    snprintf(maps_path, sizeof maps_path, "/proc/%d/maps", pid);
    FILE *m = fopen(maps_path, "r");
    if (!m) { perror("fopen(maps)"); return 1; }

    char line[512], perms[8], dev[32], path[256];
    unsigned long start = 0, end = 0, off = 0, inode = 0;
    unsigned long best_start = 0, best_len = 0;

    while (fgets(line, sizeof line, m)) {
        path[0] = 0;
        int nf = sscanf(line, "%lx-%lx %7s %lx %31s %lu %255s",
                        &start, &end, perms, &off, dev, &inode, path);
        if (nf < 6) continue;
        if (perms[0] != 'r' || perms[1] != 'w') continue;  /* rw only      */
        int anon = (nf == 6) || strcmp(path, "[heap]") == 0;
        if (!anon) continue;
        unsigned long len = end - start;
        if (len == 0 || len > (8u << 20)) continue;
        if (len > best_len) { best_start = start; best_len = len; }
    }
    fclose(m);
    if (best_len == 0) {
        fprintf(stderr, "[-] no anonymous rw region found.\n");
        return 1;
    }
    fprintf(stderr, "[*] target buffer at 0x%lx (%lu bytes)\n",
            best_start, best_len);

    char *buf = malloc(best_len);
    if (!buf) { perror("malloc"); return 1; }

    struct iovec lr = { buf, best_len };
    struct iovec rr = { (void *)best_start, best_len };
    if (process_vm_readv(pid, &lr, 1, &rr, 1, 0) < 0) {
        int e = errno;
        fprintf(stderr, "[-] process_vm_readv: %s (errno=%d).\n"
                        "    Need ptrace rights: root, or attack your own child,\n"
                        "    or ptrace_scope=0.\n", strerror(e), e);
        free(buf);
        return 1;
    }

    long at = find_bytes(buf, best_len, secret, secret_len);
    if (at < 0) {
        fprintf(stderr, "[-] secret not found in buffer.\n");
        free(buf);
        return 1;
    }

    unsigned long hit = best_start + (unsigned long)at;
    printf("[*] secret at 0x%lx: '%.32s'\n", hit, buf + at);
    printf("[*] writing '%s' over it...\n", replacement);

    struct iovec lw = { (void *)replacement, repl_len };
    struct iovec rw = { (void *)hit, repl_len };
    ssize_t n = process_vm_writev(pid, &lw, 1, &rw, 1, 0);
    if (n < 0) {
        fprintf(stderr, "[-] process_vm_writev: %s\n", strerror(errno));
        free(buf);
        return 1;
    }
    printf("[+] wrote %zd byte(s). Watch the victim's stdout.\n", n);
    free(buf);
    return 0;
}