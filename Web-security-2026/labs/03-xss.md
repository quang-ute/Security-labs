# Lab 03 — XSS (Cross-Site Scripting)

## 📖 Explanation

**XSS (Cross-Site Scripting)** injects malicious scripts into web pages
viewed by other users. The browser executes the attacker's code in the
context of the trusted origin, giving access to cookies, localStorage,
and the ability to modify the page.

### Three types in this lab

| Type | How it works | Where |
|---|---|---|
| **Reflected** | Payload is in the URL/request and echoed back immediately | `/search?q=PAYLOAD` |
| **Persistent (Stored)** | Payload is saved on the server and served to all visitors | Note content |
| **DOM-based** | Payload is processed client-side via `location.hash` | `/welcome` |

---

## 🎯 Try It

### Reflected XSS (`/search`)

1. Log in and go to **Search**.
2. Enter: `<script>alert('Reflected XSS')</script>`
3. The script executes because the query is rendered with `| safe`.

**Bypass note:** Real-world reflected XSS often requires URL-encoding.

### Persistent XSS (Notes)

1. Go to **Dashboard → New Note**.
2. Create a note with title `Test` and content:
   ```
   <script>alert('Stored XSS')</script>
   ```
3. View the note — the script executes every time someone opens it.
4. Log in as `bob` / `password2` and browse to the same note — it fires
   for Bob too! This is a **stored XSS** that affects all users.

### DOM-based XSS (`/welcome`)

1. Visit `/welcome` — the page reads `location.hash` and writes it to the DOM
   using `innerHTML`.
2. In your browser address bar, enter:
   ```
   http://127.0.0.1:15000/welcome#<img src=x onerror=alert('DOM XSS')>
   ```
3. The image tag loads, fails, and executes the `onerror` handler.

---

## 🔍 Packet Inspection with mitmproxy

XSS is one of the most instructive vulnerabilities to watch on the wire.

### Reflected XSS — What the server sends back

1. Submit the payload in the search box while mitmproxy is running.
2. Find the flow for `GET /search?q=<script>alert(1)</script>`.
3. Inspect the **Response body**:

```html
<p>You searched for: <strong><script>alert(1)</script></strong></p>
```

The `<script>` tag is in the HTML **as-is**. The browser interprets it.

Compare this to a **fixed** response where the payload would be escaped:

```html
<p>You searched for: <strong>&lt;script&gt;alert(1)&lt;/script&gt;</strong></p>
```

**This is the key distinction** — always watch for `| safe` in templates.

### Persistent XSS — Payload stored server-side

1. Create a note with XSS payload.
2. Watch the POST to `/notes/new` — the payload is in the request body.
3. When you open the note, watch the `GET /notes/<id>` response — the
   payload is embedded in the HTML served to **every** visitor.

### Cookie inspection

Look at the `Set-Cookie` header in any response:

```http
Set-Cookie: session=abc123...; HttpOnly; Path=/
```

**HttpOnly is missing** in the current app. Without it, JavaScript can
read the cookie via `document.cookie` — the XSS payload can steal the
session.

### DOM-based XSS — No server involvement

For `/welcome`, the server response is clean HTML — the XSS happens entirely
in the browser. You'll see:

1. The request: `GET /welcome` (no payload in the URL path).
2. The response is normal HTML.
3. But the **client-side** JavaScript reads `location.hash` and writes it
   via `innerHTML` — invisible to mitmproxy.

> 💡 **Takeaway:** DOM-based XSS cannot be detected by server-side traffic
> inspection. That's what makes it so sneaky.

### Use the addon

```bash
uv run mitmweb -s mitm_addon.py    # identical in PowerShell — uv resolves the venv
```

The addon flags responses containing unescaped `<script>` tags and reminds
you when `HttpOnly` is missing from cookies.

---

## 🛡️ Hardening

### Fix 1 — Contextual output escaping (Reflected & Persistent)

**Never** use `| safe` unless you have explicitly sanitised the content first.

**Wrong:**
```html
<p>You searched for: <strong>{{ query | safe }}</strong></p>
```

**Correct:** (Flask auto-escapes by default, just remove `| safe`):
```html
<p>You searched for: <strong>{{ query }}</strong></p>
```

For raw HTML that needs to allow some safe tags, use a library like
**Bleach** to sanitise:

```python
import bleach

sanitised = bleach.clean(user_content,
    tags=['b', 'i', 'u', 'em', 'strong', 'a'],
    attributes={'a': ['href', 'title']},
    strip=True)
```

Note: In the current app, `note_detail.html` uses `{{ note.content | safe }}`.
Remove the `| safe` filter.

### Fix 2 — Use `innerText` / `textContent` instead of `innerHTML` (DOM XSS)

**Vulnerable:**
```javascript
document.getElementById('greeting').innerHTML = 'Hello, <strong>' + name + '</strong>!';
```

**Fixed:**
```javascript
// Use textContent to avoid HTML injection
document.getElementById('greeting').textContent = 'Hello, ' + name + '!';
```

Or use safe DOM methods:
```javascript
var el = document.getElementById('greeting');
el.innerHTML = '';  // clear
el.appendChild(document.createTextNode('Hello, ' + name + '!'));
```

### Fix 3 — Set Content Security Policy (CSP) headers

```python
@app.after_request
def add_csp(response):
    response.headers['Content-Security-Policy'] = \
        "default-src 'self'; script-src 'self'; object-src 'none'"
    return response
```

### Fix 4 — Use `HttpOnly` cookies

```python
app.config['SESSION_COOKIE_HTTPONLY'] = True
```

This prevents JavaScript from reading the session cookie — limits damage
even if XSS is present.

### Key takeaway

> Never trust user input that ends up in HTML, JavaScript, CSS, or URLs.
> Escape output according to the context where it appears.