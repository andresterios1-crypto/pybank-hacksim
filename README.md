# PyBank HackSim

A simulated banking app (Flask + SQLite) built to learn how common web attacks
like **SQL injection** work — and how to defend against them.

> ⚠️ **Intentionally vulnerable.** Some features in this project are insecure
> *on purpose* so the attacks can be studied. All users, balances, and
> transactions are **fabricated**. Do not deploy this or reuse its code in
> anything real.

## Run it

```bash
python app.py
```

Then open http://127.0.0.1:5000

The database (`database.db`) is created automatically on first run with demo
users. It is gitignored, so each clone starts fresh.

## Demo logins

| Username | Password   |
|----------|------------|
| alice    | alice123   |
| bob      | bob123     |
| charlie  | charlie123 |

## Reset the data

The only true reset is deleting the database **file** — dropping a table or
changing balances persists to disk and survives a restart:

```bash
# stop the server first, then:
rm database.db      # (del database.db on Windows)
python app.py
```

## What I'm exploring

- Parameterized queries (`?`) vs. string-built SQL, and why the first is safe
- SQL injection through the login form (`' OR '1'='1`)
- Stacked queries (`'; DROP TABLE users; --`) and why `.execute()` blocks them
  while `.executescript()` does not
