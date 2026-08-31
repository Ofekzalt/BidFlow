import os
import subprocess
from pathlib import Path

import pytest

SETTLEMENT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://settlement:settlement@localhost:5432/settlement"
)


def _database_url() -> str:
    explicit = os.environ.get("SETTLEMENT_DATABASE_URL")
    if explicit:
        return explicit
    inherited = os.environ.get("DATABASE_URL")
    if inherited is None:
        return _DEFAULT_DATABASE_URL
    path = inherited.split("?")[0].rstrip("/")
    if path.endswith("/auction"):
        return _DEFAULT_DATABASE_URL
    return inherited


DATABASE_URL = _database_url()
os.environ["DATABASE_URL"] = DATABASE_URL
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_placeholder")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")


@pytest.fixture(scope="session")
def settlement_schema() -> None:
    env = {**os.environ, "DATABASE_URL": DATABASE_URL}
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=SETTLEMENT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
