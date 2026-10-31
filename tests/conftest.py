"""Shared fixtures.

Every test runs against a temporary SQLite database built from migrations/.
The real data/app.db is never opened.
"""
import importlib
import os
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)  # the app mounts "app/static", "app/templates" and "data/images" relative to CWD
(ROOT / "data" / "images").mkdir(parents=True, exist_ok=True)

MIGRATIONS = sorted((ROOT / "migrations").glob("*.sql"))

# Every module that holds its own copy of the DB path (see todo.md "Standardize DB_PATH").
_DB_MODULES = [
    "app.auth",
    "app.main",
    "app.models.expenses",
    "app.models.gallery",
    "app.models.health",
    "app.models.wealth",
    "app.routes.admin",
    "app.routes.auth_routes",
]


def build_db(path: Path) -> None:
    """Apply every migration in order, mirroring scripts/init_db.sh (which skips ALTERs already applied)."""
    conn = sqlite3.connect(path)
    try:
        for migration in MIGRATIONS:
            try:
                conn.executescript(migration.read_text())
            except sqlite3.OperationalError as exc:
                if "duplicate column name" not in str(exc):
                    raise
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(scope="session")
def db_path(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("db") / "app.db"
    build_db(path)
    return path


@pytest.fixture
def app_env(monkeypatch, db_path):
    """Point every DB_PATH at the temp database and give the app a valid dev environment."""
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-not-for-production")
    monkeypatch.setenv("HTTPS_ONLY", "false")
    for name in _DB_MODULES:
        monkeypatch.setattr(importlib.import_module(name), "DB_PATH", db_path)
    quotes = importlib.import_module("app.services.quotes")
    monkeypatch.setattr(quotes, "_quotes", [{"quote": "Test quote", "author": "Test", "source": ""}])
    return db_path


@pytest.fixture
def client(app_env):
    from app.main import app

    with TestClient(app, follow_redirects=False) as c:
        yield c
