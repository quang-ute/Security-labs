#!/usr/bin/env bash
# verify.sh — smoke-tests the lab's core claims on THIS machine and prints
# PASS/FAIL. Run from os-isolation-lab/ as your normal (non-root) user:
#
#   ./build.sh && ./verify.sh
#
# Privileged checks (root read, vm_readv as root) run only if `sudo -n`
# works without a password prompt; otherwise they are reported SKIP and you
# can run them interactively during the lab.
set -u
cd "$(dirname "$0")"
PATH="./:$PATH"

if [ ! -x target ] || [ ! -x mem_peek ] || [ ! -x vm_readv ]; then
    echo "[!] binaries missing — run ./build.sh first"
    exit 2
fi

SECRET="VERIFY-SECRET-$(od -An -N2 -tu2 /dev/urandom | tr -d ' ')"
PASS=0; FAIL=0; SKIP=0
ok()   { echo "  PASS: $1"; PASS=$((PASS+1)); }
bad()  { echo "  FAIL: $1"; FAIL=$((FAIL+1)); }
skip() { echo "  SKIP: $1"; SKIP=$((SKIP+1)); }

echo "==[1] ptrace_scope (should be 1 on Ubuntu; must be reported) =="
SCOPE=$(sysctl -n kernel.yama.ptrace_scope 2>/dev/null || echo "?")
[ -n "$SCOPE" ] && ok "kernel.yama.ptrace_scope=$SCOPE" || bad "cannot read sysctl"
echo "     (2/3 = even root blocked; expect default 1 here)"

sudo -n true 2>/dev/null && ROOT_OK=1 || ROOT_OK=0

echo "==[2] same-UID attacker vs non-child: /proc/PID/mem must be EPERM =="
./target "$SECRET" 120 >/tmp/vt.out 2>&1 & TPID=$!
sleep 1
if cat "/proc/$TPID/mem" >/dev/null 2>/tmp/vterr; then
    bad "cat /proc/$TPID/mem unexpectedly opened"
else
    grep -qE "Permission denied|Operation not permitted" /tmp/vterr \
        && ok "cat → $(head -1 /tmp/vterr)" \
        || bad "unexpected open error: $(head -1 /tmp/vterr)"
fi
./mem_peek "$TPID" "$SECRET" >/dev/null 2>/tmp/vperr
grep -qE "DENIED" /tmp/vperr \
    && ok "mem_peek → ptrace denial explained" \
    || bad "mem_peek did not hit the denial path: $(tail -2 /tmp/vperr | head -1)"

echo "==[3] parent-child at scope=1: allowed without root (vm_readv --child) =="
OUT=$(./vm_readv --child "$SECRET" 2>&1)
if echo "$OUT" | grep -q "SECRET at"; then
    ok "own child readable: $(echo "$OUT" | grep 'SECRET at' | head -1)"
else
    bad "child read failed: $(echo "$OUT" | tail -3 | head -1)"
fi

echo "==[4] privileged checks (root can force the door open) =="
if [ "$ROOT_OK" = 1 ]; then
    dd if="/proc/$TPID/mem" of=/dev/null bs=1 count=1 2>/dev/null
    # dd as root opens fine; reading byte 0 is EIO (no mapping at 0) — but
    # open() succeeding is what we assert here, vs cat's EPERM above.
    HDR=$(sudo -n dd if="/proc/$TPID/mem" bs=1 count=1 2>&1 >/dev/null)
    case "$HDR" in
        *"Input/output error"*) ok "root: open() succeeds (read → EIO at offset 0)" ;;
        *) bad "root open unexpected: $HDR" ;;
    esac
    if sudo -n ./mem_peek "$TPID" "$SECRET" 2>/dev/null | grep -q "SECRET FOUND"; then
        ok "root mem_peek reads the secret via /proc/PID/mem"
    else
        bad "root mem_peek failed to find secret"
    fi
    if sudo -n ./vm_readv "$TPID" "$SECRET" 2>/dev/null | grep -q "SECRET at"; then
        ok "root process_vm_readv reads the secret"
    else
        bad "root vm_readv failed"
    fi
else
    skip "root checks (no passwordless sudo) — do them manually with sudo"
fi

kill "$TPID" 2>/dev/null
wait "$TPID" 2>/dev/null

echo
echo "== summary: PASS=$PASS FAIL=$FAIL SKIP=$SKIP =="
[ "$FAIL" = 0 ]