"""Smoke tests: the app boots, public pages render, restricted pages gate, login works."""
import re
import sqlite3

from app.auth import hash_password


def _create_user(db_path, username, password, role="admin"):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, hash_password(password), role),
        )
        conn.commit()
    finally:
        conn.close()


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_public_pages_render(client):
    for path in ["/", "/blog", "/gallery", "/projects", "/login"]:
        r = client.get(path)
        assert r.status_code == 200, path
        assert "text/html" in r.headers["content-type"], path


def test_retired_library_is_404(client):
    r = client.get("/library")
    assert r.status_code == 404
    assert "text/html" in r.headers["content-type"]  # custom 404 page, not JSON


def test_restricted_pages_redirect_to_login(client):
    for path in ["/expenses", "/wealth", "/health", "/today"]:
        r = client.get(path)
        assert r.status_code in (302, 303, 307), path
        assert r.headers["location"].endswith("/login"), path


def test_login_then_restricted_page(client, app_env):
    _create_user(app_env, "smoke", "correct horse battery")

    page = client.get("/login")
    token = re.search(r'name="csrf_token"\s+value="([0-9a-f]+)"', page.text).group(1)

    r = client.post("/login", data={"username": "smoke", "password": "correct horse battery", "csrf_token": token})
    assert r.status_code == 303
    assert r.headers["location"] == "/"

    for path in ["/expenses", "/wealth", "/health", "/today"]:
        assert client.get(path).status_code == 200, path


def test_login_rejects_bad_password(client, app_env):
    _create_user(app_env, "smoke2", "right password")
    page = client.get("/login")
    token = re.search(r'name="csrf_token"\s+value="([0-9a-f]+)"', page.text).group(1)
    r = client.post("/login", data={"username": "smoke2", "password": "wrong", "csrf_token": token})
    assert r.status_code == 401
