import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_path: str
    secret_key: str
    admin_username: str
    admin_password_hash: str
    cookie_secure: bool
    frontend_path: Path


def load_settings() -> Settings:
    missing = [k for k in ("SECRET_KEY", "ADMIN_PASSWORD_HASH") if not os.environ.get(k)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. See .env.example."
        )
    return Settings(
        database_path=os.environ.get("DATABASE_PATH", str(REPO_ROOT / "data" / "growth-ledger.db")),
        secret_key=os.environ["SECRET_KEY"],
        admin_username=os.environ.get("ADMIN_USERNAME", "admin"),
        admin_password_hash=os.environ["ADMIN_PASSWORD_HASH"],
        cookie_secure=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
        frontend_path=Path(os.environ.get("FRONTEND_PATH", str(REPO_ROOT / "artifact" / "index.html"))),
    )
