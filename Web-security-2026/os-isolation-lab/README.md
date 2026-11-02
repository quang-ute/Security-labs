# OS Isolation Lab — Process Memory Isolation

A 2-hour hands-on lab about **Linux process memory isolation**:
why a process cannot read another process's memory via `/proc/[PID]/mem`,
where the real permission gate lives (ptrace + Yama), and how sanctioned
tools (`gdb`, `gcore`, `process_vm_readv/writev`) get in legitimately.

## Quick start (on Linux / WSL Ubuntu)

```bash
sudo apt-get install -y build-essential gdb     # if missing
cd os-isolation-lab
./build.sh          # compiles target, mem_peek, vm_readv, vm_writev
./verify.sh         # sanity-check: PASS should outnumber FAIL
```

Then follow **`lab.md`** (120-minute plan, includes all expected outputs
and the answer key).

## Files

| File | What it is |
|------|-----------|
| `isolation.md` | the original brief this design fulfils |
| `lab.md` | the full 2-hour lab (the thing to follow) |
| `src/target.c` | victim process holding a secret in memory |
| `src/mem_peek.c` | naive attacker via file I/O on `/proc/<pid>/mem` |
| `src/vm_readv.c` | attacker via `process_vm_readv(2)` (+ `--child` mode) |
| `src/vm_writev.c` | `process_vm_writev(2)` hot-patch demo |
| `build.sh` / `verify.sh` | build + machine self-check |

Notes:

- All binaries were validated on Ubuntu 24.04 / WSL2 (kernel 6.18) —
  expected outputs in `lab.md` come from real runs.
- `/proc/<pid>/mem` denial is reported as `EACCES` ("Permission denied")
  on this kernel; some kernels say `EPERM` ("Operation not permitted").
  Both are the same gate — the lab explains this.
- The lab toggles `kernel.yama.ptrace_scope`; **always restore it to `1`**
  (the cleanup checklist in `lab.md` does this).