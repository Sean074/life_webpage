#!/usr/bin/env python3
"""CLI to add a user to the site. Run from the project root."""
import argparse
import getpass
import sqlite3
import sys
from pathlib import Path

import bcrypt

DB_PATH = Path(__file__).parent.parent / "data" / "library.db"


def main():
    parser = argparse.ArgumentParser(description="Create a site user")
    parser.add_argument("--username", required=True)
    parser.add_argument("--role", choices=["admin", "user"], required=True)
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        sys.exit(1)

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (args.username, password_hash, args.role),
        )
        conn.commit()
        print(f"Created {args.role} user '{args.username}'.")
    except sqlite3.IntegrityError:
        print(f"Username '{args.username}' already exists.", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
