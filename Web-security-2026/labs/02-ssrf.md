# Lab 02 — SSRF (Server-Side Request Forgery)

## 📖 Explanation

**SSRF (Server-Side Request Forgery)** tricks the server into making HTTP
requests to internal or restricted resources that should not be accessible
from the outside.

The attacker provides a URL that the server fetches. If no validation is done
on the URL, the attacker can point it to:

- Internal services (`http://127.0.0.1:15000/admin`)
- Cloud metadata endpoints (`http://169.254.169.254/latest/meta-data/`)
- File-reading schemes (`file:///etc/passwd`)
- Internal network hosts not exposed to the internet

### Impact

- Read internal configuration files
- Scan internal network ports
- Access cloud instance metadata (IAM credentials)
- Bypass firewall restrictions

---

## 🎯 Try It

1. **Log in** as `alice` / `password1`.

2. Go to the **SSRF Lab** (`/ssrf`).

3. Test with a legitimate URL first:
   - Enter `http://example.com` and click **Fetch**.

4. Now try to access **internal resources**:
   - `http://127.0.0.1:15000/` — the app itself!
   - `http://127.0.0.1:15000/dashboard` — internal page behind login
   - `http://localhost:15000/`

5. Try the **file:// scheme**:
   - `file:///etc/passwd` — read system files
   - `file:///home/fie-admin/Apps/rea/web_sec/app.py` — read source code

6. Try scanning the internal network:
   - `http://192.168.1.1:80`
   - `http://10.0.0.1:22`

---

## 🔍 Packet Inspection with mitmproxy

SSRF is uniquely visible in mitmproxy because you can see **two** HTTP
exchanges for one form submission:

1. The browser → server request (the POST to `/ssrf`).
2. The server → target request (the outgoing fetch).

### What to look for

**1. The client POST**

```http
POST /ssrf HTTP/1.1
Host: 127.0.0.1:15000
Cookie: session=abc123

url=http://127.0.0.1:15000/
```

**2. The server's outbound request** (the SSRF itself)

mitmproxy intercepts this too! You'll see a **second** flow originating from
the server's IP:

```http
GET / HTTP/1.1
Host: 127.0.0.1:15000
Accept-Encoding: identity
Connection: close
```

This is the server acting as a client — hitting its own `/` endpoint.

**3. Try the `file://` scheme**

POST body: `url=file:///etc/passwd`

Watch the flow list — the addon tags it with `[SSRF]` and you can see the
response body contains `/etc/passwd` content.

### Key insight

If the internal service (`127.0.0.1:15000`) required authentication, but the
SSRF fetcher **does not forward credentials**, you can see that internal
services become exposed. With `file://`, no auth is needed at all.

### Use the addon

```bash
uv run mitmweb -s mitm_addon.py    # identical in PowerShell — uv resolves the venv
```

The addon tags SSRF requests that target `file://`, `127.0.0.1`, `localhost`,
or private IP ranges.

---

## 🛡️ Hardening

### Fix 1 — Whitelist allowed hosts/URLs

```python
import re

ALLOWED_HOSTS = {"example.com", "api.trusted-service.com"}

def is_safe_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        return False
    return True
```

### Fix 2 — Block private/internal IP ranges

```python
import ipaddress

def is_private_ip(hostname):
    try:
        addr = ipaddress.ip_address(hostname)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False
```

### Fix 3 — Disable redirect following

```python
class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # don't follow redirects

opener = urllib.request.build_opener(NoRedirectHandler)
```

### Fix 4 — Block dangerous schemes

```python
DENIED_SCHEMES = {"file", "ftp", "gopher", "dict", "ldap"}

parsed = urllib.parse.urlparse(url)
if parsed.scheme in DENIED_SCHEMES:
    return "Scheme not allowed", 400
```

### Fix 5 — Use a dedicated outbound proxy / network namespace

Route all outbound requests through a proxy that explicitly blocks private
ranges, or run the fetcher in an isolated network namespace.

### Key takeaway

> Always validate and restrict what URLs your server can fetch.
> Default: **deny all** and allow only known-good destinations.