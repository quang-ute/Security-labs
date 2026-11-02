#!/usr/bin/env python3
"""Seed the vulnerable app database with demo users and notes."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "portal.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS users;
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            bio TEXT DEFAULT ''
        );

        DROP TABLE IF EXISTS notes;
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            is_public INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # Demo users (plaintext passwords — intentionally vulnerable for the lab)
    users = [
        ("alice",   "password1", "alice@example.com",  "I love security research."),
        ("bob",     "password2", "bob@example.com",     "Just a regular student."),
        ("admin",   "supersecret", "admin@portal.local", "Administrator of the portal."),
    ]
    for u, p, e, b in users:
        cur.execute("INSERT INTO users (username,password,email,bio) VALUES (?,?,?,?)", (u, p, e, b))

    # Demo notes
    notes = [
        (1, "Research Notes",  "<b>CSRF</b> is a serious vulnerability. Always use anti-CSRF tokens."),
        (1, "Secret Todo",     "Buy more coffee. <script>alert('xss')</script>"),
        (2, "Public Note",     "This is Bob's public note."),
        (2, "Private Thoughts","Alice is really good at hacking."),
        (3, "Admin Notice",    "Reminder: change default passwords."),
    ]
    for uid, title, content in notes:
        cur.execute("INSERT INTO notes (user_id, title, content) VALUES (?,?,?)", (uid, title, content))

    con.commit()
    con.close()
    print(f"✅ Database seeded at {DB_PATH}")


if __name__ == "__main__":
    init_db()