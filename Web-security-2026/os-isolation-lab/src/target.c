/*
 * target.c — the "victim" process for the memory-isolation lab.
 *
 * It reads a secret (argv[1], else $TARGET_SECRET, else a default),
 * parks it in a 1 MiB heap buffer padded with 'A' noise, prints its PID,
 * and then just sleeps and leaks its own secret back to its own stdout
 * so the class can see it is alive.
 *
 * Build:  gcc -O0 -g -Wall -Wextra -o target target.c
 * Run:    ./target 'SUPERSECRET-PRIMARY' 300
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <signal.h>

static volatile sig_atomic_t running = 1;

static void on_signal(int sig) {
    (void)sig;
    running = 0;
}

int main(int argc, char **argv) {
    const char *secret = "SUPERSECRET-DEFAULT";
    if (argc > 1 && argv[1][0])
        secret = argv[1];
    else {
        const char *env = getenv("TARGET_SECRET");
        if (env && env[0])
            secret = env;
    }
    int seconds = (argc > 2) ? atoi(argv[2]) : 300;
    time_t deadline = time(NULL) + seconds;   /* run for `seconds` then exit */

    size_t bufsz = 1u << 20;              /* 1 MiB heap buffer */
    char  *buf  = malloc(bufsz);
    if (!buf) { perror("malloc"); return 1; }
    memset(buf, 0x41, bufsz);             /* fill with 'A' noise      */
    strcpy(buf, secret);                  /* secret parked at offset 0 */

    signal(SIGTERM, on_signal);
    signal(SIGINT,  on_signal);

    printf("TARGET pid=%d\n", getpid());
    printf("TARGET secret: '%s' at heap %p (buffer %zu bytes)\n",
           secret, (void *)buf, bufsz);
    fflush(stdout);

    while (running && time(NULL) < deadline) {
        sleep(2);
        printf("[tick] still holding '%s' @ %p\n", buf, (void *)buf);
        fflush(stdout);
    }

    printf("TARGET exiting.\n");
    free(buf);
    return 0;
}