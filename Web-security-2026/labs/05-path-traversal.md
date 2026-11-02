# Lab 05 — Path Traversal

## 📖 Explanation

**Path Traversal** (also called Directory Traversal) lets an attacker read
files outside the intended directory by using `../` sequences in file paths.

If an application takes a filename from the user and passes it to file
operations (like `send_file` or `open()`) without sanitising `../`, the
attacker can escape the uploads directory and read any file the server
process has access to.

### The vulnerable code

```python
@app.route("/files/<path:filename>")
def serve_file(filename):
    return send_file(os.path.join(UPLOAD_DIR, filename))
```

`os.path.join(UPLOAD_DIR, "../../etc/passwd")` resolves to a real path
outside `UPLOAD_DIR`, and `send_file` happily serves it.

---

## 🎯 Try It

### 1. Upload a file first (so there's something to fetch normally)

Log in, go to **Upload**, upload a simple text file (e.g., `hello.txt`).

### 2. Access it normally

Visit: `http://127.0.0.1:15000/files/hello.txt`

### 3. Traverse up

Now try to read system files:

| URL | Expected result |
|---|---|
| `http://127.0.0.1:15000/files/../app.py` | Source code of the app |
| `http://127.0.0.1:15000/files/../../etc/passwd` | System user list |
| `http://127.0.0.1:15000/files/../../../etc/shadow` | Password hashes (may be perm-denied) |

### 4. Try URL-encoded variants

Some servers decode URL-encoded characters before passing to the filesystem:

- `http://127.0.0.1:15000/files/%2e%2e/app.py` (`%2e` = `.`)
- `http://127.0.0.1:15000/files/..%252f..%252fapp.py` (double encoding)

### 5. Try the note attachment route too

`http://127.0.0.1:15000/notes/attachment/../app.py`

---

## 🔍 Packet Inspection with mitmproxy

Path traversal is immediately visible in the request URL.

### What to look for

**1. Normal file request**

```http
GET /files/hello.txt HTTP/1.1
Host: 127.0.0.1:15000
```

**2. Path traversal attack**

```http
GET /files/%2e%2e/app.py HTTP/1.1
Host: 127.0.0.1:15000
```

Notice:
- `%2e%2e` is the URL-encoded form of `..` (`.` = `%2e`).
- You can also see double-encoded attempts: `%252e%252e`.
- The browser sends `../` as-is, but curl and some clients normalise it.

### Response analysis

The response body contains the **source code of the app** — something the
user should never see:

```http
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8

#!/usr/bin/env python3
"""
WSS (Web Security School) — A deliberately vulnerable Flask application.
...
```

Compare this to a normal response where `Content-Type` would be
`application/octet-stream` and the file content would be binary (for images)
or plain text.

### Watch the server-side path resolution

In mitmproxy's flow details, you can't see the server-side `os.path.join()`
result directly, but you can infer it from the response: if you get
`/etc/passwd` content back, the server resolved
`/uploads/../../etc/passwd` → `/etc/passwd`.

### Use the addon

```bash
uv run mitmweb -s mitm_addon.py    # identical in PowerShell — uv resolves the venv
```

The addon flags any request to `/files/` or `/notes/attachment/` containing
`%2e` or `..` with a `[Path Traversal]` tag.

---

## 🛡️ Hardening

### Fix 1 — Resolve and validate the absolute path

```python
import os

def safe_send_file(filename, base_dir):
    # Resolve to absolute path
    abs_path = os.path.realpath(os.path.join(base_dir, filename))
    base_dir = os.path.realpath(base_dir)

    # Ensure the resolved path is inside the base directory
    if not abs_path.startswith(base_dir + os.sep):
        return "Access denied", 403

    return send_file(abs_path)
```

### Fix 2 — Whitelist allowed filenames (no user-controlled paths)

```python
ALLOWED_FILES = {"report.pdf", "avatar.png", "notes.txt"}

if filename not in ALLOWED_FILES:
    return "File not found", 404
```

### Fix 3 — Use file IDs instead of filenames

Store files with a UUID or database-generated ID, and map IDs to actual
files server-side:

```python
# Store mapping in DB
file_id = "a1b2c3d4"
actual_path = "/var/uploads/a1b2c3d4.pdf"

# User requests /files/a1b2c3d4
# Server looks up the actual path internally
```

### Fix 4 — Strip or reject `..` sequences

```python
if ".." in filename or filename.startswith("/"):
    return "Invalid filename", 400
```

> ⚠️ This alone is not sufficient — bypasses exist (e.g., URL encoding,
> double encoding, symbolic links). Combine with Fix 1.

### Fix 5 — Run the file-serving component in a chroot / container

If files must be served, isolate the serving process so that even a
traversal can't reach sensitive files.

### Key takeaway

> Resolve paths to their canonical form and verify they stay within the
> intended directory. Never trust user-supplied filenames.