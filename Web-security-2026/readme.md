# 🔬 WSS — Web Security School

A deliberately vulnerable Flask web application for learning web security.
Designed for beginners to **exploit**, **understand**, and then **fix** 10
common web vulnerabilities.

---

## 🚀 Quick Start

```bash
# Git Bash / WSL / Linux
uv sync              # builds .venv from pyproject.toml + uv.lock
uv run init_db.py    # seed the database
uv run app.py        # start on http://127.0.0.1:15000
```

```powershell
# PowerShell (Windows) — same commands, no venv activation needed
uv sync
uv run init_db.py
uv run app.py
```

**Demo accounts:**

| User  | Password    |
| ----- | ----------- |
| alice | password1   |
| bob   | password2   |
| admin | supersecret |

---

## 📋 Vulnerability Labs

| #  | Vulnerability                                       | Route                               | Lab Guide                                                   |
| -- | --------------------------------------------------- | ----------------------------------- | ----------------------------------------------------------- |
| 01 | **CSRF** — Cross-Site Request Forgery        | `/profile`                        | [labs/01-csrf.md](labs/01-csrf.md)                           |
| 02 | **SSRF** — Server-Side Request Forgery       | `/ssrf`                           | [labs/02-ssrf.md](labs/02-ssrf.md)                           |
| 03 | **XSS** — Reflected, Persistent, DOM-based   | `/search`, Notes, `/welcome`    | [labs/03-xss.md](labs/03-xss.md)                             |
| 04 | **SQLi** — SQL Injection                     | `/login`                          | [labs/04-sqli.md](labs/04-sqli.md)                           |
| 05 | **Path Traversal** — Directory Traversal     | `/files/`, `/notes/attachment/` | [labs/05-path-traversal.md](labs/05-path-traversal.md)       |
| 06 | **File Upload** — Unrestricted Upload        | `/upload`                         | [labs/06-file-upload.md](labs/06-file-upload.md)             |
| 07 | **IDOR** — Insecure Direct Object Reference  | `/notes/<id>`                     | [labs/07-idor.md](labs/07-idor.md)                           |
| 08 | **Command Injection** — OS Command Injection | `/ping`                           | [labs/08-command-injection.md](labs/08-command-injection.md) |
| 09 | **SSTI** — Server-Side Template Injection    | `/greet`                          | [labs/09-ssti.md](labs/09-ssti.md)                           |
| 10 | **Open Redirect** — Unvalidated Redirect     | `/logout`, `/proxy`             | [labs/10-open-redirect.md](labs/10-open-redirect.md)         |

---

## 🔍 Packet Inspection with mitmproxy

Every lab includes a **🔍 Packet Inspection** section that teaches you to
watch the raw HTTP traffic using **mitmproxy**.

### Why packet inspection?

- See the **exact payload** sent over the wire (URL-encoded, POST body, etc.)
- Watch **cookies** being transmitted automatically
- Observe **server-to-server requests** (SSRF, redirects)
- Compare **before vs after hardening** responses
- Find the vulnerability by looking at headers and body, not just the UI

### Quick start

```bash
# Terminal 1: Start the vulnerable app
uv run app.py

# Terminal 2: Start mitmproxy with the WSS addon
uv run mitmweb -s mitm_addon.py --listen-host 127.0.0.1 --listen-port 18080 --set web_port=18081

# Browser: Proxy → 127.0.0.1:18080, then visit http://127.0.0.1:15000
```

```powershell
# PowerShell: the same two commands work unchanged (uv resolves the venv)
uv run app.py
uv run mitmweb -s mitm_addon.py --listen-host 127.0.0.1 --listen-port 18080 --set web_port=18081
```

Full setup guide → [`mitmproxy-setup.md`](mitmproxy-setup.md)

---

## 📚 How to Use This Lab

### For each vulnerability, follow this cycle:

1. **📖 Read the explanation** — Understand what the vulnerability is and why it's dangerous.
2. **🔍 Watch the traffic** — Use mitmproxy to observe the normal HTTP flow.
3. **🎯 Exploit it** — Use the provided examples to trigger the vulnerability. Watch the raw packets change in mitmproxy.
4. **🛡️ Apply the hardening** — Implement the fixes in `app.py` or the templates. Each lab guide shows multiple hardening strategies.
5. **✅ Verify the fix** — Try the same exploit again. Watch the traffic — the attack payload should no longer produce the vulnerable behaviour.

### Learning tips

- Start with the **simpler** labs (SQLi, XSS, CSRF) before moving to advanced ones (SSTI, SSRF).
- Try to develop your **own payloads** beyond the examples given.
- For **SSTI and Command Injection**, understand the *mechanism* — don't just copy payloads.
- After fixing one vulnerability, check if the fix **introduces another** (e.g., over-escaping breaking functionality).

---

## ⚠️ Important Warnings

> **🚨 DO NOT** deploy this application on a public network, cloud server, or anywhere accessible outside your local machine. It is intentionally vulnerable.

> **🔒** Run only on `127.0.0.1` (localhost). The app binds to `127.0.0.1` by default.

> **📁** The lab guides and app source are in `web_sec/`. All paths in the guides are relative to this directory.

---

## 🏗️ Architecture

```
web_sec/
├── app.py                  # Flask app (all vulnerabilities)
├── init_db.py              # Database seeder
├── requirements.txt        # Dependencies
├── portal.db               # SQLite database (auto-created)
├── uploads/                # Uploaded files
├── index.md                # This file
├── mitmproxy-setup.md      # mitmproxy configuration guide
├── mitm_addon.py           # mitmproxy addon (auto-tags vulnerabilities)
├── templates/              # Jinja2 templates
│   ├── base.html           # Layout & navigation
│   ├── index.html          # Home page
│   ├── login.html          # SQLi vulnerable login
│   ├── register.html       # Registration
│   ├── dashboard.html      # User dashboard
│   ├── profile.html        # CSRF vulnerable profile
│   ├── note_detail.html    # Persistent XSS & IDOR
│   ├── search.html         # Reflected XSS
│   ├── welcome.html        # DOM-based XSS
│   ├── ssrf.html           # SSRF lab
│   ├── ping.html           # Command injection lab
│   ├── upload.html         # File upload lab
│   └── 404.html
└── labs/
    ├── 01-csrf.md          # Lab guides ...
    ├── 02-ssrf.md
    ├── 03-xss.md
    ├── 04-sqli.md
    ├── 05-path-traversal.md
    ├── 06-file-upload.md
    ├── 07-idor.md
    ├── 08-command-injection.md
    ├── 09-ssti.md
    └── 10-open-redirect.md
```

---

## 🧪 Extending the Lab

- Add **rate limiting** to teach defence against brute-force
- Add **JWT tokens** and show JWT vulnerabilities
- Add **WebSocket** endpoints for real-time XSS
- Add **CAPTCHA** alongside CSRF tokens
- Containerise with Docker for reproducible lab environments
