import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _bool(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    jwt_secret: str = field(default_factory=lambda: os.environ.get("JWT_SECRET") or "dev-secret-change-me")
    jwt_expire_minutes: int = 1440
    db_path: str = field(default_factory=lambda: os.environ.get("DB_PATH") or str(BACKEND_DIR / "data" / "app.db"))
    frontend_origins: list = field(
        default_factory=lambda: [
            o.strip()
            for o in (os.environ.get("FRONTEND_ORIGINS") or "http://localhost:3000").split(",")
            if o.strip()
        ]
    )
    groq_api_key: str = field(default_factory=lambda: os.environ.get("GROQ_API_KEY", ""))
    gemini_api_key: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    groq_model: str = field(default_factory=lambda: os.environ.get("GROQ_MODEL") or "llama-3.3-70b-versatile")
    gemini_model: str = field(default_factory=lambda: os.environ.get("GEMINI_MODEL") or "gemini-2.0-flash")
    upload_dir: str = field(default_factory=lambda: os.environ.get("UPLOAD_DIR") or str(BACKEND_DIR / "data" / "uploads"))
    max_file_bytes: int = 5_242_880
    max_files_per_submission: int = 30
    max_submission_bytes: int = 26_214_400
    llm_mock: bool = field(default_factory=lambda: _bool("LLM_MOCK"))


settings = Settings()
