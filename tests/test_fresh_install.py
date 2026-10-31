"""A fresh checkout or a fresh deploy must boot and render without the gitignored data files,
and must not care which directory the server was started from (issues #7 and #10)."""
import importlib

from fastapi.testclient import TestClient

from app.services import quotes


def test_random_quote_without_quotes_csv(monkeypatch, tmp_path):
    monkeypatch.setattr(quotes, "QUOTES_CSV", tmp_path / "quotes.csv")
    monkeypatch.setattr(quotes, "_quotes", [])
    assert quotes.random_quote() is None


def test_random_quote_with_header_only_csv(monkeypatch, tmp_path):
    csv_path = tmp_path / "quotes.csv"
    csv_path.write_text("quote,author,source\n")
    monkeypatch.setattr(quotes, "QUOTES_CSV", csv_path)
    monkeypatch.setattr(quotes, "_quotes", [])
    assert quotes.random_quote() is None


def test_pages_render_without_quotes_csv(client, monkeypatch, tmp_path):
    monkeypatch.setattr(quotes, "QUOTES_CSV", tmp_path / "quotes.csv")
    monkeypatch.setattr(quotes, "_quotes", [])
    r = client.get("/")
    assert r.status_code == 200
    assert "quote-footer" not in r.text


def test_app_serves_files_from_any_cwd(app_env, monkeypatch, tmp_path):
    # Start the app from an unrelated directory: static files, templates and posts must still resolve.
    monkeypatch.chdir(tmp_path)
    app = importlib.import_module("app.main").app
    with TestClient(app, follow_redirects=False) as c:
        assert c.get("/static/css/main.css").status_code == 200
        home = c.get("/")
        assert home.status_code == 200 and "text/html" in home.headers["content-type"]
        blog = c.get("/blog")
        assert blog.status_code == 200
        assert "building-this-site" in blog.text  # a post from content/posts/, found without the CWD
        assert c.get("/art/does-not-exist.jpg").status_code == 404
