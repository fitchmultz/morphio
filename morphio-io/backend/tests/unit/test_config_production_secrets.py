"""Purpose: Regression tests for backend production secret hardening.
Responsibilities: Prove placeholder/default secret values are rejected in production mode.
Scope: Settings initialization safeguards for SECRET_KEY and JWT_SECRET_KEY.
Usage: Executed in backend unit tests and fast CI checks.
Invariants/Assumptions: Production requires non-placeholder secrets and a non-SQLite DATABASE_URL.
"""

import pytest

from app.config import Settings


def _set_minimal_production_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@localhost:5432/morphio")
    monkeypatch.setenv("SECRET_KEY", "strong_secret_key_value")
    monkeypatch.setenv("JWT_SECRET_KEY", "strong_jwt_secret_key_value")


@pytest.mark.parametrize(
    "invalid_secret", ["", "dev_secret_key", "__GENERATE_SECURE_VALUE__", "__CHANGE_ME__"]
)
def test_production_rejects_invalid_secret_key(
    monkeypatch: pytest.MonkeyPatch, invalid_secret: str
) -> None:
    _set_minimal_production_env(monkeypatch)
    monkeypatch.setenv("SECRET_KEY", invalid_secret)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings()


@pytest.mark.parametrize(
    "invalid_jwt_secret",
    ["", "dev_jwt_secret_key", "__GENERATE_SECURE_VALUE__", "__CHANGE_ME__"],
)
def test_production_rejects_invalid_jwt_secret_key(
    monkeypatch: pytest.MonkeyPatch, invalid_jwt_secret: str
) -> None:
    _set_minimal_production_env(monkeypatch)
    monkeypatch.setenv("JWT_SECRET_KEY", invalid_jwt_secret)

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        Settings()
