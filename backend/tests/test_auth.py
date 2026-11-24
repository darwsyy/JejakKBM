import pytest

from app.auth import DEVELOPMENT_SECRET_KEY, load_secret_key


def test_development_environment_can_use_local_fallback():
    assert load_secret_key("development", None) == DEVELOPMENT_SECRET_KEY


def test_production_requires_configured_secret():
    with pytest.raises(RuntimeError, match="wajib diatur"):
        load_secret_key("production", None)


def test_production_rejects_development_secret():
    with pytest.raises(RuntimeError, match="wajib diatur"):
        load_secret_key("production", DEVELOPMENT_SECRET_KEY)


def test_production_rejects_short_secret():
    with pytest.raises(RuntimeError, match="minimal 32 karakter"):
        load_secret_key("production", "too-short-secret")


def test_production_accepts_long_configured_secret():
    configured = "a-unique-production-secret-with-more-than-32-chars"
    assert load_secret_key("production", configured) == configured
