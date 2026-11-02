# Lab 10 — Open Redirect

## 📖 Explanation

**Open Redirect** occurs when an application accepts a URL parameter and
redirects the browser to that URL without validation.

An attacker can craft a link that looks like it goes to the legitimate site
but actually redirects to a malicious one. This is commonly used in:

- **Phishing campaigns** — victims see a trusted domain in the link preview
- **Credential harvesting** — redirect to a fake login page
- **Bypassing URL filters** — some spam filters check the visible domain

### The vulnerable routes

```python
@app.route("/logout")
def logout():
    next_param = request.args.get("next", "")
    if next_param:
        return redirect(next_param)  # no validation!
    ...
```

```python
@app.route("/proxy")
def proxy():
    target = request.args.get("to", "/")
    return redirect(target)  # no validation!
```

---

## 🎯 Try It

### 1. Logout redirect

While logged in, visit:

```
http://127.0.0.1:15000/logout?next=http://evil.com
```

You're redirected to `http://evil.com`. A real attacker would make this
look like a logout link: `https://portal.example.com/logout?next=http://evil-phishing-page.com`

### 2. Proxy redirect

```
http://127.0.0.1:15000/proxy?to=http://example.com
```

Visiting this URL redirects to `http://example.com`.

### 3. Open redirect to `javascript:` (bypass some filters)

```
http://127.0.0.1:15000/proxy?to=javascript:alert('XSS')
```

### 4. Double redirect (evasion)

```
http://127.0.0.1:15000/proxy?to=http://127.0.0.1:15000/proxy?to=http://evil.com
```

### 5. Using `//` to bypass domain checks

If validation only checks for `http://`:

```
http://127.0.0.1:15000/proxy?to=//evil.com
```

This redirects to `http://evil.com` (protocol-relative).

---

## 🔍 Packet Inspection with mitmproxy

Open redirect is all about the **response status code and Location header**.

### What to look for

**1. Logout with normal redirect**

Request:
```http
GET /logout HTTP/1.1
Host: 127.0.0.1:15000
Cookie: session=abc123
```

Response:
```http
HTTP/1.1 302 FOUND
Location: /
```

A 302 redirect to `/` — normal behaviour.

**2. Open redirect attack**

Request:
```http
GET /logout?next=http://evil.com HTTP/1.1
Host: 127.0.0.1:15000
Cookie: session=abc123
```

Response:
```http
HTTP/1.1 302 FOUND
Location: http://evil.com/          ← external site!
```

The `Location` header points to an **external** domain. This is the
signature of an open redirect.

**3. Proxy route**

```http
GET /proxy?to=http://phishing.com HTTP/1.1
```

```http
HTTP/1.1 302 FOUND
Location: http://phishing.com/
```

### What a fixed response looks like

After hardening, the same request would either:

- Return a **403 Forbidden**:
  ```http
  HTTP/1.1 403 FORBIDDEN
  Invalid redirect target
  ```

- Or redirect only to the whitelisted path:
  ```http
  HTTP/1.1 302 FOUND
  Location: /dashboard          ← relative, safe
  ```

### Cryptocurrency/phishing angle

In the wild, open redirects are used to make phishing URLs look legitimate:

```
https://legitimate-bank.com/logout?next=https://legitimate-bank-login.com
```

The first domain is real, but the redirect sends the user to a fake site.

### Use the addon

```bash
uv run mitmweb -s mitm_addon.py    # identical in PowerShell — uv resolves the venv
```

The addon flags any 3xx response whose `Location` header points outside
`127.0.0.1:15000` and tags it `[Open Redirect]`.

---

## 🛡️ Hardening

### Fix 1 — Whitelist allowed redirect targets

```python
ALLOWED_REDIRECTS = {
    url_for("index"),
    url_for("dashboard"),
    url_for("profile"),
}

def is_safe_redirect(target):
    return target in ALLOWED_REDIRECTS
```

### Fix 2 — Use relative URLs only and validate them

```python
from urllib.parse import urlparse

def is_safe_redirect(target):
    parsed = urlparse(target)
    # Allow only relative URLs (no scheme, no netloc)
    return not parsed.scheme and not parsed.netloc
```

### Fix 3 — Compare against the application's host

```python
def is_safe_redirect(target):
    parsed = urlparse(target)
    # Must have the same host
    return parsed.hostname in ("127.0.0.1", "localhost") or \
           parsed.hostname == request.host
```

### Fix 4 — Use a mapping instead of a URL parameter

Instead of passing `?next=http://example.com/page`, use a key:

```python
# In the app
REDIRECT_MAP = {
    "home": "index",
    "dash": "dashboard",
    "profile": "profile",
}

@app.route("/proxy")
def proxy():
    key = request.args.get("to", "home")
    if key not in REDIRECT_MAP:
        return "Invalid redirect target", 400
    return redirect(url_for(REDIRECT_MAP[key]))
```

### Fix 5 — Display a confirmation page for external redirects

```python
@app.route("/external-redirect")
def external_redirect():
    target = request.args.get("to")
    # Show a page: "You are leaving the site. Click to continue."
    return render_template("redirect_warning.html", target=target)
```

### Fix 6 — Set `Referrer-Policy` headers

```python
@app.after_request
def add_headers(response):
    response.headers['Referrer-Policy'] = 'no-referrer'
    return response
```

This prevents the target site from seeing where the user came from.

### Key takeaway

> Never redirect users to arbitrary URLs from your domain.
> If you must redirect, whitelist the allowed destinations.