"""
PyBank - a simple local banking app built with Flask + SQLite.

Run:   python app.py
Open:  http://127.0.0.1:5000
Stop:  Ctrl+C in the terminal

This is the "normal" baseline version. Later we'll copy it and add
vulnerabilities on purpose for the hacking simulator.
"""

import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (Flask, flash, g, redirect, render_template, request,
                   session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

app = Flask(__name__)
# Random key each time the server starts -> everyone gets logged out on restart.
app.secret_key = os.urandom(24)


# ---------------------------------------------------------------- database ---

def get_db():
    """Open one database connection per request."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row  # lets us use row["column_name"]
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the tables and some demo users (only if the DB doesn't exist)."""
    if os.path.exists(DB_PATH):
        return

    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        CREATE TABLE users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name     TEXT NOT NULL,
            balance_cents INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE transactions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id    INTEGER NOT NULL REFERENCES users(id),
            receiver_id  INTEGER NOT NULL REFERENCES users(id),
            amount_cents INTEGER NOT NULL,
            note         TEXT,
            created_at   TEXT NOT NULL
        );
    """)

    # Money is stored in cents (integers) to avoid floating-point errors.
    demo_users = [
        ("alice",   "alice123",   "Alice Johnson",  150000),  # $1,500.00
        ("bob",     "bob123",     "Bob Smith",       80000),  # $800.00
        ("charlie", "charlie123", "Charlie Brown",   25000),  # $250.00
        ("andres", "andres123", "Andres Monasterios",    1000000),
    ]
    for username, password, full_name, balance in demo_users:
        db.execute(
            "INSERT INTO users (username, password_hash, full_name, balance_cents) "
            "VALUES (?, ?, ?, ?)",
            (username, generate_password_hash(password), full_name, balance),
        )

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    db.executemany(
        "INSERT INTO transactions (sender_id, receiver_id, amount_cents, note, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (1, 2, 2500, "Pizza night", now),
            (2, 3, 1000, "Movie tickets", now),
            (3, 1, 500, "Coffee", now),
        ],
    )
    db.commit()
    db.close()
    print("Created database.db with demo users.")


# ------------------------------------------------------------------ helpers ---

def login_required(view):
    """Decorator: send the user to the login page if they aren't logged in."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    return get_db().execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()


@app.template_filter("money")
def money(cents):
    """Use in templates: {{ user.balance_cents | money }} -> $1,500.00"""
    return f"${cents / 100:,.2f}"


# ------------------------------------------------------------------- routes ---

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # --- SAFE VERSION (commented out so we can compare) ---
        # Parameterized query (the "?") = safe from SQL injection.
        # user = get_db().execute(
        #     "SELECT * FROM users WHERE username = ?", (username,)
        # ).fetchone()

        # --- VULNERABLE VERSION (your turn) ---
        query = "SELECT * FROM users WHERE username = '" + username + "'"
        # .execute()       -> one statement only (blocks ';'-stacked attacks)
        # .executescript() -> many statements allowed (DROP TABLE etc. work!)
        user = get_db().executescript(query).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    transactions = get_db().execute(
        """
        SELECT t.*, s.username AS sender, r.username AS receiver
        FROM transactions t
        JOIN users s ON s.id = t.sender_id
        JOIN users r ON r.id = t.receiver_id
        WHERE t.sender_id = ? OR t.receiver_id = ?
        ORDER BY t.id DESC
        """,
        (user["id"], user["id"]),
    ).fetchall()
    return render_template("dashboard.html", user=user, transactions=transactions)


@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    user = current_user()
    db = get_db()

    if request.method == "POST":
        to_username = request.form.get("to", "").strip()
        note = request.form.get("note", "").strip()[:100]

        # --- validate the amount ---
        try:
            amount_cents = round(float(request.form.get("amount", "")) * 100)
        except ValueError:
            amount_cents = 0

        receiver = db.execute(
            "SELECT * FROM users WHERE username = ?", (to_username,)
        ).fetchone()

        if amount_cents <= 0:
            flash("Enter an amount greater than $0.", "error")
        elif receiver is None:
            flash("That user doesn't exist.", "error")
        elif receiver["id"] == user["id"]:
            flash("You can't send money to yourself.", "error")
        elif amount_cents > user["balance_cents"]:
            flash("Insufficient funds.", "error")
        else:
            # Move the money and record it, all in one database transaction.
            with db:
                db.execute(
                    "UPDATE users SET balance_cents = balance_cents - ? WHERE id = ?",
                    (amount_cents, user["id"]),
                )
                db.execute(
                    "UPDATE users SET balance_cents = balance_cents + ? WHERE id = ?",
                    (amount_cents, receiver["id"]),
                )
                db.execute(
                    "INSERT INTO transactions "
                    "(sender_id, receiver_id, amount_cents, note, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user["id"], receiver["id"], amount_cents, note,
                     datetime.now().strftime("%Y-%m-%d %H:%M")),
                )
            flash(f"Sent {money(amount_cents)} to {receiver['username']}.", "success")
            return redirect(url_for("dashboard"))

    others = db.execute(
        "SELECT username, full_name FROM users WHERE id != ? ORDER BY username",
        (user["id"],),
    ).fetchall()
    return render_template("transfer.html", user=user, others=others)


if __name__ == "__main__":
    init_db()
    # 127.0.0.1 = only reachable from THIS computer.
    app.run(host="127.0.0.1", port=5000, debug=True)
