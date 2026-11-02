# 🔍 mitmproxy Setup for WSS Labs

This guide shows you how to intercept and inspect HTTP traffic between your
browser and the vulnerable web app using **mitmproxy**.

Why? Because seeing the raw request/response headers, cookies, and bodies
gives you a much deeper understanding of what each vulnerability actually
does on the wire.

---

## 📦 What you need

- **mitmproxy** — already installed in the project's `.venv`
- **A browser** — Firefox or Chrome
- **The WSS app** running on `http://127.0.0.1:15000`

---

## ⚙️ Basic mitmproxy Modes

### Mode A — mitmweb (GUI, recommended for beginners)

```bash
source .venv/bin/activate
mitmweb --listen-host 127.0.0.1 --listen-port 18080 --set web_port=18081
```

Opens a web UI at `http://127.0.0.1:18081` where you can click on each
request and see headers, cookies, and body.

### Mode B — mitmproxy (TUI, lightweight)

```bash
source .venv/bin/activate
mitmproxy --listen-host 127.0.0.1 --listen-port 18080
```

Keyboard shortcuts: `up`/`down` to select, `Enter` to inspect,
`q` to go back, `:` to enter commands.

### Mode C — mitmdump (CLI, scripting)

```bash
source .venv/bin/activate
mitmdump --listen-host 127.0.0.1 --listen-port 18080 -w traffic.flow
```

Records all traffic to `traffic.flow` for later replay/inspection.

---

## 🔐 Install the mitmproxy CA Certificate

mitmproxy generates its own TLS certificate authority. For this lab the app
runs over **HTTP**, so you don't strictly need it — just configure the proxy.

*If you later test HTTPS sites, install the cert:*

1. Start mitmproxy, then visit `http://mitm.it` from the proxied browser.
2. Download the certificate for your OS.
3. Follow OS-specific instructions to trust it.

---

## 🧭 Configure your browser

### Firefox

```
Settings → Network Settings → Manual proxy configuration
  HTTP Proxy: 127.0.0.1  Port: 18080
  ☑ Also use this proxy for HTTPS
  No proxy for: localhost, 127.0.0.1
```

Then browse to `http://127.0.0.1:15000` — traffic goes through mitmproxy.

### Chrome

```
Settings → System → Open your computer's proxy settings
  (Or use a proxy-switcher extension)
```

Alternatively, launch Chrome with the proxy flag:

```bash
google-chrome --proxy-server=127.0.0.1:18080 --incognito
```

### curl (CLI)

```bash
curl -x http://127.0.0.1:18080 http://127.0.0.1:15000/login
```

---

## 🎯 What to look for per lab

| Lab                         | What to watch in mitmproxy                                                                                         |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **CSRF**              | POST body has **no** anti-CSRF token. Cookies sent automatically.                                            |
| **SSRF**              | The server makes a *second* request from its own IP. Watch for `file://` or `127.0.0.1` in the outgoing URL. |
| **XSS**               | Response body contains raw `<script>` tags. Session cookie lacks `HttpOnly` flag.                              |
| **SQLi**              | The injected SQL payload appears in the POST body. The server responds with a successful login.                    |
| **Path Traversal**    | Request path contains `%2e%2e/` (URL-encoded `../`). Response returns a system file.                           |
| **File Upload**       | Multipart POST body shows the raw file content. Accessing the uploaded file returns it directly.                   |
| **IDOR**              | Request URL has a numeric ID. Changing it returns a **different** user's note.                               |
| **Command Injection** | POST body contains shell metacharacters (`;`, `                                                                  |
| **SSTI**              | Request URL contains `{{7*7}}`. Response has `49` — Jinja2 evaluated it server-side.                          |
| **Open Redirect**     | Response is a **302** with a `Location` header pointing to an external site.                               |

---

## 🧪 Custom Addon

The file `mitm_addon.py` (in this directory) provides a mitmproxy addon that
automatically highlights vulnerability-related patterns. Run it with:

```bash
mitmproxy -s mitm_addon.py --listen-host 127.0.0.1 --listen-port 18080
# or
mitmweb -s mitm_addon.py --listen-host 127.0.0.1 --listen-port 18080 --set web_port=18081
```

The addon annotates flows with tags like `[SQLi]`, `[XSS]`, `[SSTI]`, etc.
and logs suspicious patterns to the event log (press `E` in mitmproxy TUI).

---

## 💡 Quick workflow

```bash
# Terminal 1: Run the vulnerable app
source .venv/bin/activate && cd web_sec && python app.py

# Terminal 2: Run mitmweb
source .venv/bin/activate && mitmweb -s web_sec/mitm_addon.py

# Browser: Proxy → 127.0.0.1:18080, then visit http://127.0.0.1:15000
```

Use **mitmweb's web UI** (`http://127.0.0.1:18081`) to click through requests.
Watch the headers, cookies, and bodies as you exploit each vulnerability.
