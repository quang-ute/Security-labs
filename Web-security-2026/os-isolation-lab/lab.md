# Lab — Linux Process Memory Isolation

**Duration:** 120 minutes · **Level:** intermediate (some C/shell) · **Environment:** any recent Linux (verified on Ubuntu 24.04 / WSL2, kernel 6.18)

> Do not run the "privileged" steps on a machine you do not own. This lab
> inspects process memory of ordinary processes **you spawned yourself**;
> run it on your own workstation or in a disposable VM/container.

---

## 🎯 Objectives

By the end you will be able to:

| # | Objective | Covered in |
|---|-----------|-----------|
| 1 | Explain the fundamental security principle of process memory isolation in Linux | Part 1 |
| 2 | Demonstrate that a process **cannot** read another process's memory via standard file I/O on `/proc/[PID]/mem` | Part 2 |
| 3 | Explain **why** the kernel blocks this direct access (ptrace permission model, Yama LSM, capabilities) | Part 2 + Part 3 |
| 4 | Contrast the failed direct access with **sanctioned** methods: `gdb` and the `process_vm_readv(2)` syscall | Part 4 |
| 5 | Bonus demonstrations you can do with the same tooling | Part 5 |

---

## 🗂️ Files in this folder

| File | Purpose |
|------|---------|
| `src/target.c` | "victim": parks a secret in a 1 MiB heap buffer, prints its PID and the secret's address, then ticks forever |
| `src/mem_peek.c` | "naive attacker": plain `open()` + `pread()` on `/proc/<pid>/mem` |
| `src/vm_readv.c` | attacker via the `process_vm_readv(2)` syscall (also `--child` mode) |
| `src/vm_writev.c` | attacker writing into a live process via `process_vm_writev(2)` |
| `build.sh` | compiles everything with `gcc` |
| `verify.sh` | smoke-test: checks the lab's core claims on *your* machine (PASS/FAIL) |
| `isolation.md` | the lab brief this design fulfils |

---

## ⏱️ Time plan

| Block | Time | You will… |
|-------|------|-----------|
| 0. Setup | 10 min | build tools, spawn the victim, sanity-check `ptrace_scope` |
| 1. Address spaces & ASLR | 15 min | see that every process lives in its own virtual address space |
| 2. The forbidden direct read | 25 min | attack `/proc/[PID]/mem` — and watch the kernel say no |
| 3. The gatekeeper: ptrace & Yama | 15 min | find the *actual* permission gate and flip it deliberately |
| 4. Sanctioned access | 30 min | read/steal the secret properly: `gdb`, `gcore`, `process_vm_readv`, and hot-patch with `process_vm_writev` |
| 5. Bonus observations | 15 min | `maps` vs `environ` vs `pagemap` leaks; ASLR drift |
| 6. Wrap-up & quiz | 10 min | concept map, why this protects you, checkpoint questions |

---

## Part 0 — Setup (10 min)

```bash
# Ubuntu / Debian only if the tools are missing:
sudo apt-get update && sudo apt-get install -y build-essential gdb

cd os-isolation-lab
./build.sh
./verify.sh        # should say PASS for the "denied" and "parent" checks
```

What you should see (exact PIDs / addresses differ):

```
[*] building with gcc -O0 -g -Wall -Wextra
[+] done. Binaries: target mem_peek vm_readv vm_writev

==[1] ptrace_scope (should be 1 on Ubuntu; must be reported) ==
  PASS: kernel.yama.ptrace_scope=1
==[2] same-UID attacker vs non-child: /proc/PID/mem must be EPERM ==
  PASS: cat → cat: /proc/1192/mem: Permission denied
  PASS: mem_peek → ptrace denial explained
==[3] parent-child at scope=1: allowed without root (vm_readv --child) ==
  PASS: own child readable: [+] process_vm_readv: SECRET at 0x7198caa31010
== summary: PASS=4 FAIL=0 ==
```

Record the kernel's stance on debuggers — it is the star of this lab:

```bash
sysctl kernel.yama.ptrace_scope
```

```
kernel.yama.ptrace_scope = 1
```

---

## Part 1 — Every process lives in its own world (15 min)

### Background

A running program is a **process**: an isolated execution context with its
own view of memory. What the process calls "address `0x1000`" is an address
in its **virtual address space**, which the CPU + MMU translate to physical
RAM via page tables. Two processes may use the *same* virtual address for
completely different physical memory. On a context switch the kernel swaps
page tables — process A literally cannot even *address* process B's memory
without the kernel's help.

> 📌 The kernel( MMU) is therefore the only component that can map between
> one process's view and another's. *Any* cross-process memory access —
> legitimate or malicious — must go through the kernel. That's the
> foundation of everything in this lab.

### See "self"

```bash
cat /proc/self/maps | head -8
```

`/proc/<pid>/maps` is a map of one process's address space: each line is
`start-end perms offset device inode pathname`. Everything below the binary
itself lives at randomized, per-process addresses (ASLR).

### See ASLR (randomization) at work

```bash
for i in 1 2 3; do
  cat /proc/self/maps | head -1
  sleep 1
done
```

Three runs → three *different* base addresses. The kernel is already
hiding *where* things live, in addition to *who may read them*:

```
5d25a9c0a000-5d25a9c0b000 r--p ...
5d25c24a3000-5d25c24a4000 r--p ...      ← different base every time
5dbc527a6000-5dbc527a7000 r--p ...
```

### Spawn the victim

```bash
./target 'SUPERSECRET-PRIMARY' 300
```

Output (addresses are per-run):

```
TARGET pid=779
TARGET secret: 'SUPERSECRET-PRIMARY' at heap 0x757bd0aff010 (buffer 1048576 bytes)
[tick] still holding 'SUPERSECRET-PRIMARY' @ 0x757bd0aff010
```

The victim:
- holds the secret in a **1 MiB heap buffer**;
- prints the secret **and its exact address** (convenient — attackers do not
  get this printed, but the address is discoverable via `/proc/<pid>/maps`);
- ticks every 2 seconds so you can watch it stay alive.

Record the PID: `TPID=<pid>` in your second terminal (any terminal works —
the whole point is that this process is **not your child**).

---

## Part 2 — The forbidden direct read (25 min)

### 2.1 The naive attack

A completely plausible first attempt: the secret is in the process's
memory, `/proc/<pid>/mem` is *a file*… so `cat` it:

```bash
cat /proc/$TPID/mem > /dev/null
```

```
cat: /proc/779/mem: Permission denied
```

Same user (`id -u` equals the victim's UID), yet denied. Try `dd`, try
Python's `open()`:

```bash
dd if=/proc/$TPID/mem of=/dev/null bs=1 count=1
python3 -c "import sys; open(f'/proc/{sys.argv[1]}/mem','rb').read(1)" "$TPID"
```

Every path fails identically. This is our attacker tool with the detailed
diagnosis:

```bash
./mem_peek $TPID SUPERSECRET-PRIMARY
```

```
[*] largest anonymous rw region: 0x757bd0aff000 (1052672 bytes)
[-] open(/proc/779/mem): Permission denied (errno=13)
    => DENIED: the kernel refuses ptrace-style access.
       Same UID is NOT enough under ptrace_scope=1 for a
       non-child. That gate is the ENTIRE point of this lab.
```

> 🕵️ Note the diagnostic line: `mem_peek` first reads `/proc/<pid>/maps`
> — which **succeeded**. The layout is public; the *contents* are protected.

### 2.2 Two separate gates

There are two distinct gates, and it is worth learning to tell them apart.

**Gate 1 — permission.** Opening `/proc/<pid>/mem` runs a full
`ptrace_may_access()` check (same code path the `ptrace(2)` syscall uses).
No permission → `open()` fails with `EACCES`/`EPERM`. This is the gate that
stopped us.

**Gate 2 — address validity.** Even with permission, `read()` only
succeeds for addresses inside the target's actual mappings. Memory is not
a contiguous file — `offset 0` of the "file" means *virtual address 0*,
which is unmapped. Root can prove this:

```bash
sudo cat /proc/$TPID/mem | head -c 16
```

```
cat: /proc/779/mem: Input/output error      ← open() OK … read() EIO
```

`EIO` here is the kernel saying "that byte is not yours to read **because
no mapping exists at that address**". To read anything you must first learn
real addresses — which is exactly what `mem_peek`'s "largest anonymous rw
region" line is doing when it parses `maps`.

### 2.3 The mandatory root dent

A skeptic will say "surely root can read it":

```bash
sudo cat /proc/$TPID/mem               # EIO again (offset 0 = unmapped)
sudo ./mem_peek $TPID SUPERSECRET-PRIMARY
```

```
[*] largest anonymous rw region: 0x7e4f520ec000 (1064960 bytes)
[+] open(/proc/779/mem) succeeded (caller has ptrace rights)
[+] SECRET FOUND at 0x7e4f520ec010:
    'SUPERSECRET-PRIMARY'
    000010  53 55 50 45 52 53 45 43 52 45 54 2d 50 52 49 4d
    000020  00 41 41 41 41 41 41 41 41 41 41 41 41 41 41 41
```

Root (more precisely: **`CAP_SYS_PTRACE`**) can force both gates open — it
has the same privilege `gdb` uses. Notice the hexdump: `SUPERSECRET-PRIMARY`
followed by `00` and the `A` noise that pads the buffer.

**Checkpoint Q1:** why does `sudo cat` fail but `sudo ./mem_peek` succeed?
*(Answer: gate 2 — offset 0 is not mapped; mem_peek seeks to a real region
from `maps` first.)*

### 2.4 Why does the kernel block this?

Think about what your machine holds in memory right now: SSH private keys,
browser session cookies, the password for whatever sudo just asked, API
tokens, decrypted mail. Hundreds of processes, thousands of secrets — all
co-resident in RAM. If any same-UID user could `cat /proc/*/mem`, then a
single compromised user account could harvest the **entire machine**:

- keylog-free password theft (the password is in memory somewhere),
- session hijacking (steal any browser's cookie jar from RAM),
- credential dumping (like `mimikatz` — but it wouldn't even need `ptrace`).

The kernel therefore treats *other processes' memory as privileged
resources*, grants access through an explicit permission model
(`ptrace_may_access`, gated by credentials, capabilities, and the Yama LSM),
and refuses everything else — even between two processes owned by the same
user. Isolation is not a bug you work around; it is the design.

---

## Part 3 — The gatekeeper: ptrace & Yama (15 min)

### 3.1 What is actually deciding?

Open `/proc/<pid>/mem` → the kernel calls `ptrace_may_access()`, which
checks, roughly in order:

1. **Dumpable / credentials** — same real UID, or `CAP_SYS_PTRACE`;
2. **LSM hooks** — on Ubuntu/Debian this is where **Yama** applies its
   `ptrace_scope` policy.

Inspect the Yama knob:

```bash
sysctl kernel.yama.ptrace_scope
cat /proc/sys/kernel/yama/ptrace_scope
```

| Value | Meaning |
|-------|---------|
| `0` | any process with matching UID may trace any other (classic Unix) |
| `1` (Ubuntu/Debian default) | only the **parent** may trace its child; root with `CAP_SYS_PTRACE` still may |
| `2` | only root may trace |
| `3` | no one may trace (even root) — kiosk/hardening mode |

### 3.2 Relationship qualifies where identity does not

At scope `1`, *parenthood* counts for more than *the same username*. Our
`vm_readv --child` mode forks its own victim — the attacker **is** the
parent:

```bash
./vm_readv --child SUPERSECRET-LIVE
```

```
TARGET pid=765
TARGET secret: 'SUPERSECRET-LIVE' at heap 0x793a000ff010 (buffer 1048576 bytes)
[*] reading OUR OWN CHILD pid=765 (parent allowed at scope=1)
[+] process_vm_readv: SECRET at 0x793a000ff010
    'SUPERSECRET-LIVE'
```

No root, default sysctls — but the kernel allowed it, because a parent is
trusted to inspect (and steer) its child; that trust is exactly what
debuggers and shells need.

### 3.3 Deliberately weakening the gate (and restoring it)

To see what *pre-Yama* Unix looked like, an admin can set scope `0` —
**understand: this weakens the whole system, not just this lab**:

```bash
sudo sysctl -w kernel.yama.ptrace_scope=0
./vm_readv $TPID SUPERSECRET-LIVE     # same-UID sibling: NOW succeeds
./mem_peek  $TPID SUPERSECRET-LIVE    # and so does the naive file-I/O attack
```

```
sysctl: kernel.yama.ptrace_scope = 0
[+] process_vm_readv: SECRET at 0x5f23f52eb752
[+] SECRET FOUND at 0x5f23f52eb752:
```

Restore immediately — this is a security configuration:

```bash
sudo sysctl -w kernel.yama.ptrace_scope=1
sysctl kernel.yama.ptrace_scope        # must print 1 again
```

**Checkpoint Q2:** with scope `0`, both the "naive" file-I/O path and the
syscall path succeed. What does that tell you about where the real
protection lives? *(Answer: not in the file plumbing — in the shared
ptrace permission model. `/proc/<pid>/mem` and `process_vm_readv` are two
front-doors with the same lock.)*

**Checkpoint Q3:** at scope `2`, can root still read the secret? At `3`?
Try: `sudo sysctl -w kernel.yama.ptrace_scope=2` → `sudo ./mem_peek $TPID …`
then restore `1`.

---

## Part 4 — Sanctioned access (30 min)

The point of the permission model is not "no one may look" — it is "only
callers the policy trusts". Every method below uses the *same* ptrace gate;
the difference is that the caller qualifies.

### 4.1 `gdb` — the debugger

**Attach fails for a sibling** (same reason as Part 2):

```bash
gdb -q -batch -p $TPID
```

```
Could not attach to process.  If your uid matches the uid of the target
process, check the setting of /proc/sys/kernel/yama/ptrace_scope, or try
again as the root user.  For more details, see /etc/sysctl.d/10-ptrace.conf
```

**Attach succeeds when the policy trusts you** — as root (or with the
target as your child):

```bash
sudo gdb -q -batch -p $TPID -ex "x/3s 0xADDRESS"
```

using the address the victim printed (e.g. `0x757bd0aff010`):

```
0x757bd0aff010: "SUPERSECRET-PRIMARY"
0x757bd0aff01b: 'A' <repeats 200 times>...
0x757bd0aff0e3: 'A' <repeats 200 times>...
```

**Search + extract in one go** (interactive recommended; these are batch
equivalents):

```bash
# find: locate the secret anywhere in the 1 MiB buffer
ADDR=0x757bd0aff010; END=$(printf '0x%x' $((ADDR + 1048576)))
sudo gdb -q -batch -p $TPID -ex "find $ADDR, $END, \"SUPERSECRET-PRIMARY\""

# dump: copy the first 64 bytes of that region to a file
sudo gdb -q -batch -p $TPID -ex "dump binary memory /tmp/hdr.bin $ADDR 0x$(printf '%x' $((ADDR+64)))"
xxd /tmp/hdr.bin | head -2
```

```
00000000: 5355 5045 5253 4543 5245 542d 5052 494d  SUPERSECRET-PRIM
00000010: 4141 4141 4141 4141 4141 4141 4141 4141  AAAAAAAAAAAAAAAA
```

**`gcore` — one-shot memory snapshot** (the "allowed" way to dump, used
by forensic tooling):

```bash
gcore -o /tmp/gcore $TPID          # root
strings /tmp/gcore.$TPID | grep -m1 SUPERSECRET-PRIMARY
```

```
[Inferior 1 (process 964) detached]    ← gdb library unloaded the core
SUPERSECRET-PRIMARY
```

A forensic tool gets exactly what the direct attack was denied — the
difference is the **interface**: gdb/gcore go through the sanctioned
ptrace API with a properly trusted caller.

### 4.2 `process_vm_readv(2)` — the syscall interface

`process_vm_readv` is the kernel's *explicit, documented* cross-process
read syscall (used by `gdb` itself on Linux). Same permission model —
demonstrate both sides:

```bash
./vm_readv $TPID SUPERSECRET-PRIMARY      # sibling: EPERM (denied)
```

```
[-] process_vm_readv(pid=779, 0x757bd0aff000, 1052672 bytes): Operation not permitted (errno=1)
    => EPERM: same gate as /proc/779/mem. Same UID is not
       enough under ptrace_scope=1 unless you are the
       target's parent (or root, or scope=0).
```

```bash
sudo ./vm_readv $TPID SUPERSECRET-PRIMARY # root: success
```

```
[+] process_vm_readv: SECRET at 0x757bd0aff010
    'SUPERSECRET-PRIMARY'
```

Compare the two errors from Parts 2 and 4:

| Attempt | Interface | Result |
|---------|-----------|--------|
| `cat /proc/PID/mem` | file I/O | `Permission denied` (EACCES) |
| `mem_peek` | file I/O | `Permission denied` (EACCES) |
| `vm_readv` (same UID) | syscall | `Operation not permitted` (EPERM) |
| `vm_readv --child` | syscall, parent | **success, no root** |
| `sudo mem_peek` | file I/O, root | **success** |
| `sudo vm_readv` | syscall, root | **success** |
| scope=0, same UID | anything | **success** |

> 📌 The filesystem file was never the vulnerability and never the
> protection — the *ptrace permission model* is. `/proc/<pid>/mem` is
> literally implemented on top of the same permission checks.

### 4.3 `process_vm_writev(2)` — hot-patching a live process

Writing into a running process's memory is what game trainers, debuggers,
and some injectors do. Our `vm_writev` locates the secret, overwrites it in
place, and the victim's *own stdout* shows the change a tick later:

```bash
sudo ./vm_writev $TPID SUPERSECRET-PRIMARY
# …and 2 seconds later, the victim's window shows:
[tick] still holding 'HACKED!!!-MARY' @ 0x757bd0aff010
```

```
[*] target buffer at 0x757bd0aff000 (1064960 bytes)
[*] secret at 0x757bd0aff010: 'SUPERSECRET-PRIMARY'
[*] writing 'HACKED!!!-' over it...
[+] wrote 10 byte(s). Watch the victim's stdout.
```

Read it again to confirm the patch stuck:

```bash
sudo ./vm_readv $TPID 'HACKED!!!'
```

**Checkpoint Q4:** why is `HACKED!!!-MARY` (and not `HACKED!!!-`) shown by
the victim? *(The write replaced the first 10 bytes; the remaining bytes
of the original string are still there.)*

---

## Part 5 — Bonus observations (15 min, pick any)

**5a. `maps` is a free address-leak while `mem` is protected.**
Contrast what *any* user can read about a process:

```bash
head -3 /proc/$TPID/maps          # layout: OK (no privilege needed)
tr '\0' '\n' < /proc/$TPID/environ | grep -E '^(HOME|PATH|TARGET_SECRET)'
cat /proc/$TPID/pagemap > /dev/null    # per-page physical frame info
```

`maps` (layout) and `environ` (environment, same-UID) leak — `pagemap`
(physical frame numbers) is root-only since kernel 4.0. This is the
"adjacent leaks" reality of `/proc`: metadata leaks, contents don't.

**5b. Secret passed via environment is already halfway out.**
`target.c` accepts `TARGET_SECRET` from the environment; an attacker with
only the same UID can read it with no ptrace at all:

```bash
TARGET_SECRET='ENV-LEAK-99' ./target 60 &
tr '\0' '\n' < /proc/$(pgrep -n target)/environ | grep TARGET_SECRET
```

```
TARGET_SECRET=ENV-LEAK-99        ← read by a sibling, no ptrace involved
```

Moral: environment variables are not a safe place for secrets on a shared
box — `environ` is readable by the same UID.

**5c. Core dumps are a sanctioned memory dump too.** `ulimit -c unlimited`
+ crash, or `gcore` (Part 4), and `strings` the ELF core — a "memory
snapshot" you can replay offline. This is exactly how post-mortem
debugging and some malware forensics work.

**5d. Containers do not repeal ptrace.** In Docker, processes in a *different
PID namespace* are simply not visible to `/proc` and the kernel since 4.8
additionally blocks cross-namespace ptrace without `CAP_SYS_PTRACE` — try
`cat /proc/1/mem` from inside a container vs. on the host. (Need Docker
running; not required for this lab.)

---

## Part 6 — Wrap-up (10 min)

### Concept map

```
                    +-------------------------------+
                    |  process A's address space    |
   attacker ———► try read ———► KERNEL (the only      |
                    |         | cross-process path)  |
                    |         v                     |
                    |  ptrace_may_access:           |
                    |    UID / CAP_SYS_PTRACE       |
                    |    + Yama ptrace_scope        |──► DENY (Part 2)
                    |         | allow?              |
                    |         v                     |
                    |  address-validity check       |──► EIO if unmapped
                    |         | ok?                 |
                    |         v                     |
                    |   copy_to_user / vm_readv     |──► SUCCESS (Part 4)
                    +-------------------------------+
```

### Why this keeps you safe

- Secrets live in RAM by necessity; the kernel gates every cross-process
  read behind an explicit, credential-checked permission model.
- Defense-in-depth: per-process isolation (hardware paging) **+** ptrace
  permission model **+** Yama LSM **+** ASLR hiding addresses **+**
  root-only `/proc/<pid>/pagemap`.
- Modern layers on top: SELinux/AppArmor, seccomp filters, containers and
  PID namespaces, and kernel page-table isolation.
- Honesty clause: isolation is about *direct* access. **Side channels**
  (cache timing — Spectre/Meltdown class) leak *indirectly* and are a
  separate, ongoing battle; that is why your kernel gets melted-patch
  updates.

### Checkpoint quiz

1. Why does `sudo cat /proc/$PID/mem` fail even though root passed the
   permission gate?
2. Where does `/proc/<pid>/mem` get its permission checks from?
3. Name the three things the ptrace gate inspects.
4. What does Yama's `ptrace_scope=1` allow that `0` does not?
5. Two processes, one user, scope=1, attacker not a parent: which of
   `mem_peek`, `vm_readv`, `gdb -p` succeed? Why?
6. What is the *one* structural difference between the denied attack and
   the successful `process_vm_readv` call?
7. `process_vm_writev` succeeded on a running process. What capability or
   relationship did the caller need?
8. Which `/proc/<pid>` files leak to same-UID users, and why does that
   matter for `environ`?
9. Does a container (new PID namespace) make a process readable by
   `process_vm_readv` from the host? Why not?
10. Why is ASLR a defense even though `maps` is world-readable?

**Answer keys** — flip through your own outputs: Q1 gate 2 (EIO); Q2
`ptrace_may_access`/proc internals; Q3 UID-or-cap, Yama scope, dumpable;
Q4 parenthood; Q5 none of the sibling tools — same gate; Q6 none — the
*permission result* differs (parent/root vs sibling), interface is the
same model; Q7 ptrace rights (root / parent / scope=0); Q8 `maps`,
`environ`, `stat*` — same-UID, no ptrace; Q9 no — different PID namespace,
no `/proc` visibility, kernel blocks cross-namespace ptrace; Q10 ASLR makes
the *contents* of the leak unlocatable without help — it converts a
reliable exploit primitive into a search.

### Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `cat: /proc/PID/mem: Permission denied` | The gate working as intended (scope ≥ 1, sibling) |
| `cat: /proc/PID/mem: Input/output error` | Gate 1 passed, gate 2: offset 0 is unmapped — seek to a real region |
| `ptrace: Operation not permitted` (gdb) | Same gate; use root, a parent process, or `--child` |
| A tool says "not found" for the secret | Wrong PID (target died?); secret arg must match exactly; wrong region heuristic — re-run `verify.sh` |
| `vm_readv --child` prints nothing | The child uses `./target` from the *current* directory — run from the folder containing `target` |
| All privileged steps fail | You lack `sudo`/`CAP_SYS_PTRACE`; do 4.1–4.3 as root or skip (lab still works for Parts 2–3 goals) |
| `ptrace_scope` shows `0` | Some distros default `0`; either accept the different Part 2 result (everything succeeds) or set `1` for the class |

### Cleanup

```bash
# kill victims (careful: kills ALL instances of this lab's target)
pkill -f '/\./target|/target ' ; pkill -x target
# restore the security default if you toggled it
sudo sysctl -w kernel.yama.ptrace_scope=1
rm -f /tmp/gcore.* /tmp/hdr.bin
# optional: remove build artifacts in the lab folder
rm -f target mem_peek vm_readv vm_writev
```

---

## 👨‍🏫 Instructor notes

- **Pre-flight:** run `./verify.sh` once; if `ptrace_scope` is `0`, either
  set it to `1` for the class or adapt Part 2's expected output.
- **Don't run the target under `sudo`**: the "sibling denied" demos need a
  same-UID victim (Part 2). Keep victims in a plain terminal and run the
  *attacker* tools as root only in 2.3/4.1–4.3.
- **Cast the narrative as "two gates":** students conflate them. The
  2.2 root-`cat`→`EIO` moment is the one that makes it click.
- **`gdb` interactively is worth 5 minutes** over batch mode: let them
  `Ctrl-C` a running inferior, `find` the secret, and `dump` it.
- **Pacing:** Parts 2–3 are the must-haves (objectives 2–3). If a class
  runs late, cut Part 5 stretch items and compress Part 4.3.
- **Safety:** this manipulates only processes the student owns; still, a
  disposable VM/container is the cleanest venue. Changing
  `kernel.yama.ptrace_scope` weakens the host — always restore to `1`
  (it is in the lab's cleanup checklist).
- **Grades/lab report idea:** have students produce the 4×2 table from
  Part 4.2 (interface × caller) and explain, in one paragraph, why `mem`
  and `process_vm_readv` share a gate.