"""SECRET_KEY startup check and the login rate limiter."""
import time

import pytest

from app import auth
from app.routes import auth_routes


# --- SECRET_KEY ---------------------------------------------------------------

def test_production_refuses_unset_secret(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("HTTPS_ONLY", "true")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        auth.check_secret_key()


def test_production_refuses_empty_secret(monkeypatch):
    # A copied .env.example leaves SECRET_KEY= empty; that must not pass.
    monkeypatch.setenv("SECRET_KEY", "")
    monkeypatch.setenv("HTTPS_ONLY", "true")
    with pytest.raises(RuntimeError):
        auth.check_secret_key()


def test_production_refuses_dev_default(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", auth._DEFAULT_SECRET)
    monkeypatch.setenv("HTTPS_ONLY", "true")
    with pytest.raises(RuntimeError):
        auth.check_secret_key()


def test_production_starts_with_real_secret(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    monkeypatch.setenv("HTTPS_ONLY", "true")
    auth.check_secret_key()  # no raise, no warning (pytest.ini turns app warnings into errors)


def test_dev_warns_but_starts(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("HTTPS_ONLY", "false")
    with pytest.warns(UserWarning, match="SECRET_KEY"):
        auth.check_secret_key()


# --- login rate limiter -------------------------------------------------------

@pytest.fixture
def clock(monkeypatch):
    """Controllable time.time() for the auth_routes module."""
    state = {"now": 1_000_000.0}
    monkeypatch.setattr(auth_routes.time, "time", lambda: state["now"])
    monkeypatch.setattr(auth_routes, "_failures", {})
    monkeypatch.setattr(auth_routes, "_last_prune", state["now"])
    return state


def test_check_does_not_create_entries(clock):
    assert auth_routes._is_rate_limited("10.0.0.1") is False
    assert auth_routes._failures == {}


def test_limit_after_five_failures(clock):
    for _ in range(auth_routes._RATE_LIMIT - 1):
        auth_routes._record_failure("10.0.0.1")
    assert auth_routes._is_rate_limited("10.0.0.1") is False
    auth_routes._record_failure("10.0.0.1")
    assert auth_routes._is_rate_limited("10.0.0.1") is True


def test_entry_removed_once_window_passes(clock):
    auth_routes._record_failure("10.0.0.1")
    clock["now"] += auth_routes._RATE_WINDOW + 1
    assert auth_routes._is_rate_limited("10.0.0.1") is False
    assert "10.0.0.1" not in auth_routes._failures


def test_prune_sweeps_stale_ips(clock):
    for i in range(50):
        auth_routes._record_failure(f"10.0.0.{i}")
    assert len(auth_routes._failures) == 50

    # Within the window a new failure does not trigger a sweep.
    clock["now"] += auth_routes._RATE_WINDOW / 2
    auth_routes._record_failure("10.0.1.1")
    assert len(auth_routes._failures) == 51

    # After the window, the next recorded failure sweeps everything stale.
    clock["now"] += auth_routes._RATE_WINDOW
    auth_routes._record_failure("10.0.2.2")
    assert set(auth_routes._failures) == {"10.0.2.2"}
