#!/usr/bin/env python3
"""
WSS (Web Security School) — A deliberately vulnerable Flask application.

Vulnerabilities covered:
  CSRF | SSRF | XSS (reflected/persistent/DOM) | SQLi | Path Traversal
  File Upload | IDOR | Command Injection | SSTI | Open Redirect

DO NOT DEPLOY THIS ON A REAL NETWORK.  LOCALHOST / LAB USE ONLY.
"""
import os
import sys
import subprocess  # noqa: used for command injection
import urllib.request
import urllib.parse
import sqlite3

from flask import (
    Flask, request, render_template, render_template_string,
    redirect, url_for, session, send_file, make_response,
)

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
# Windows consoles / redirected output may default to cp1252 and choke on the
# emoji in the startup banner — force UTF-8 on the standard streams.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

PORT = 15000
BASE = os.path.dirname(os.path.abspath(__file__))
# ping's "count" flag differs per OS: Windows uses -n, Linux/macOS use -c.
PING_COUNT_FLAG = "-n" if os.name == "nt" else "-c"
app = Flask(__name__)
app.secret_key = "insecure-secret-key"  # intentionally weak
UPLOAD_DIR = os.path.join(BASE, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(BASE, "portal.db")


def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def logged_in_user():
    """Return the current user dict or None."""
    uid = session.get("user_id")
    if not uid:
        return None
    con = get_db()
    user = con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    con.close()
    return dict(user) if user else None


# ============================================================================
# ROUTES
# ============================================================================

@app.route("/")
def index():
    return render_template("index.html", user=logged_in_user())


# ---------------------------------------------------------------------------
# Auth (no CSRF protection on state-changing actions → CSRF vulnerability)
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        # VULN: SQLi in login
        con = get_db()
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        user = con.execute(query).fetchone()
        con.close()
        if user:
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html", error=None)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form.get("email", "")
        con = get_db()
        try:
            con.execute("INSERT INTO users (username,password,email) VALUES (?,?,?)",
                        (username, password, email))
            con.commit()
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Username taken")
        finally:
            con.close()
        return redirect(url_for("login"))
    return render_template("register.html", error=None)


@app.route("/logout")
def logout():
    # VULN: open redirect
    next_param = request.args.get("next", "")
    if next_param:
        return redirect(next_param)
    session.clear()
    return redirect(url_for("index"))


# VULN: CSRF — email update has no token check
@app.route("/profile", methods=["GET", "POST"])
def profile():
    user = logged_in_user()
    if not user:
        return redirect(url_for("login"))
    if request.method == "POST":
        new_email = request.form.get("email", user["email"])
        new_bio = request.form.get("bio", user["bio"])
        con = get_db()
        con.execute("UPDATE users SET email=?, bio=? WHERE id=?",
                    (new_email, new_bio, user["id"]))
        con.commit()
        con.close()
        return redirect(url_for("profile"))
    return render_template("profile.html", user=user)


# ---------------------------------------------------------------------------
# Dashboard & notes
# ---------------------------------------------------------------------------
@app.route("/dashboard")
def dashboard():
    user = logged_in_user()
    if not user:
        return redirect(url_for("login"))
    con = get_db()
    notes = con.execute("SELECT * FROM notes WHERE user_id=?", (user["id"],)).fetchall()
    con.close()
    return render_template("dashboard.html", user=user, notes=notes)


@app.route("/notes/<int:note_id>")
def note_detail(note_id):
    user = logged_in_user()
    if not user:
        return redirect(url_for("login"))
    con = get_db()
    note = con.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    con.close()
    if not note:
        return "Note not found", 404
    # VULN: IDOR — no ownership check
    return render_template("note_detail.html", note=note, user=user)


@app.route("/notes/new", methods=["GET", "POST"])
def new_note():
    user = logged_in_user()
    if not user:
        return redirect(url_for("login"))
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        con = get_db()
        con.execute("INSERT INTO notes (user_id, title, content) VALUES (?,?,?)",
                    (user["id"], title, content))
        con.commit()
        con.close()
        return redirect(url_for("dashboard"))
    return render_template("new_note.html")


@app.route("/notes/edit/<int:note_id>", methods=["GET", "POST"])
def edit_note(note_id):
    user = logged_in_user()
    if not user:
        return redirect(url_for("login"))
    con = get_db()
    note = con.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    if not note:
        con.close()
        return "Note not found", 404
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        con.execute("UPDATE notes SET title=?, content=? WHERE id=?",
                    (title, content, note_id))
        con.commit()
        con.close()
        return redirect(url_for("dashboard"))
    con.close()
    return render_template("edit_note.html", note=note)


# ---------------------------------------------------------------------------
# VULN: Reflected XSS — search echoes query unsanitized
# ---------------------------------------------------------------------------
@app.route("/search")
def search():
    user = logged_in_user()
    query = request.args.get("q", "")
    return render_template("search.html", query=query, user=user)


# ---------------------------------------------------------------------------
# VULN: DOM-based XSS — client uses location.hash
# ---------------------------------------------------------------------------
@app.route("/welcome")
def welcome():
    user = logged_in_user()
    return render_template("welcome.html", user=user)


# ---------------------------------------------------------------------------
# VULN: SSRF — fetch an external URL
# ---------------------------------------------------------------------------
@app.route("/ssrf", methods=["GET", "POST"])
def ssrf():
    user = logged_in_user()
    result = None
    if request.method == "POST":
        url = request.form.get("url", "")
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                result = resp.read().decode("utf-8", errors="replace")[:2000]
        except Exception as e:
            result = f"Error: {e}"
    return render_template("ssrf.html", user=user, result=result)


# ---------------------------------------------------------------------------
# VULN: Path traversal — serve files by name
# ---------------------------------------------------------------------------
@app.route("/files/<path:filename>")
def serve_file(filename):
    # VULN: no path sanitisation — allows ../ traversal
    return send_file(os.path.join(UPLOAD_DIR, filename))


@app.route("/notes/attachment/<path:filename>")
def note_attachment(filename):
    """Same vuln but via a different route for demo clarity."""
    return send_file(os.path.join(UPLOAD_DIR, filename))


# ---------------------------------------------------------------------------
# VULN: File upload — no type/content validation
# ---------------------------------------------------------------------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    user = logged_in_user()
    message = None
    if request.method == "POST":
        f = request.files.get("file")
        if f and f.filename:
            f.save(os.path.join(UPLOAD_DIR, f.filename))
            message = f"Uploaded {f.filename}"
        else:
            message = "No file selected"
    return render_template("upload.html", user=user, message=message)


# ---------------------------------------------------------------------------
# VULN: Command injection — ping tool
# ---------------------------------------------------------------------------
@app.route("/ping", methods=["GET", "POST"])
def ping():
    user = logged_in_user()
    output = None
    if request.method == "POST":
        target = request.form.get("target", "")
        # VULN: unsanitised input passed directly to shell
        try:
            output = subprocess.check_output(
                f"ping {PING_COUNT_FLAG} 3 {target}",
                shell=True,
                stderr=subprocess.STDOUT,
                timeout=10,
            ).decode("utf-8", errors="replace")
        except subprocess.CalledProcessError as e:
            # Surface what the shell actually printed — otherwise a failed
            # payload just says "returned non-zero exit status" with no clue why.
            written = (e.output or b"").decode("utf-8", errors="replace").strip()
            output = written or f"Command failed with exit status {e.returncode}."
        except subprocess.TimeoutExpired as e:
            written = (e.output or b"").decode("utf-8", errors="replace").strip()
            output = ("Command timed out after 10s.\n" + written).rstrip()
        except Exception as e:
            output = str(e)
    return render_template("ping.html", user=user, output=output)


# ---------------------------------------------------------------------------
# VULN: SSTI — user name rendered as template
# ---------------------------------------------------------------------------
@app.route("/greet")
def greet():
    user = logged_in_user()
    name = request.args.get("name", "Guest")
    # VULN: renders user input as a Jinja2 template
    template = f"<h2>Hello, {name}!</h2><p>Welcome to the portal.</p>"
    return render_template_string(template, user=user)


# ---------------------------------------------------------------------------
# VULN: Open redirect (also on /logout above)
# ---------------------------------------------------------------------------
@app.route("/proxy")
def proxy():
    target = request.args.get("to", "/")
    return redirect(target)


# ============================================================================
# Error handlers — also contain DOM XSS demo in templates
# ============================================================================
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# ============================================================================
# Entry point
# ============================================================================
if __name__ == "__main__":
    print("🔥 WSS — Web Security School  (DO NOT EXPOSE TO NETWORK)")
    print(f"   Listening on http://127.0.0.1:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)