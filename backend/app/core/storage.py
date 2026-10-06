import os
import re
from pathlib import Path

from app.core.config import settings
from app.core.errors import AppError

TEXT_EXTS = {
    "txt", "md", "py", "js", "ts", "tsx", "jsx", "json", "html", "css", "c", "h", "cpp", "hpp", "java", "sql",
    "yaml", "yml", "csv", "ino", "m", "r", "sh", "toml", "ini", "xml", "rst", "tex", "cfg", "env", "go", "rs",
    "kt", "swift", "php", "rb", "ipynb", "log", "gitignore",
}
BINARY_EXTS = {
    "png", "jpg", "jpeg", "gif", "bmp", "webp", "ico", "pdf", "zip", "gz", "tar", "7z", "rar", "exe", "dll",
    "so", "bin", "o", "class", "pyc", "docx", "xlsx", "pptx", "mp3", "mp4", "wav", "mov", "woff", "woff2", "ttf",
}


def _root() -> Path:
    return Path(os.environ.get("UPLOAD_DIR") or settings.upload_dir)


def safe_path(path: str) -> str:
    p = (path or "").replace("\\", "/").strip()
    while p.startswith("./"):
        p = p[2:]
    if not p or len(p) > 300:
        raise AppError(422, "VALIDATION_ERROR", "Invalid file path")
    if p.startswith("/") or re.match(r"^[A-Za-z]:", p):
        raise AppError(422, "VALIDATION_ERROR", "Absolute paths are not allowed")
    parts = []
    for seg in p.split("/"):
        if seg == "" or seg == "..":
            raise AppError(422, "VALIDATION_ERROR", "Invalid file path")
        if seg == ".":
            continue
        parts.append(seg)
    if not parts:
        raise AppError(422, "VALIDATION_ERROR", "Invalid file path")
    return "/".join(parts)


def _abs(storage_path: str) -> Path:
    root = _root().resolve()
    full = (root / storage_path).resolve()
    if root != full and root not in full.parents:
        raise AppError(422, "VALIDATION_ERROR", "Invalid storage path")
    return full


def save_file(project_id: str, file_id: str, data: bytes) -> str:
    rel = f"{project_id}/{file_id}"
    full = _abs(rel)
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(data)
    return rel


def read_file(storage_path: str) -> bytes:
    full = _abs(storage_path)
    if not full.is_file():
        raise AppError(404, "NOT_FOUND", "File content not found")
    return full.read_bytes()


def delete_file(storage_path: str) -> None:
    try:
        _abs(storage_path).unlink()
    except FileNotFoundError:
        pass


def decode_text(data: bytes):
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def is_text(filename: str, data: bytes) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in BINARY_EXTS:
        return False
    # Known text extensions and unknown extensions both require clean UTF-8 without NUL bytes.
    return decode_text(data) is not None
