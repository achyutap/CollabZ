import importlib
import logging
import os
import pkgutil
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.db import get_conn, init_db
from app.core.errors import register_handlers

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app.main")


def _auto_seed() -> None:
    if os.environ.get("AUTO_SEED", "true").strip().lower() == "false":
        return
    conn = get_conn()
    try:
        empty = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    finally:
        conn.close()
    if not empty:
        return
    try:
        from seed.seed import run
    except ImportError:
        log.info("No seed module found; skipping auto-seed")
        return
    try:
        result = run()
        log.info("Auto-seed finished: %s", result)
    except Exception:
        log.error("Auto-seed failed:\n%s", traceback.format_exc())


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    os.makedirs(os.environ.get("UPLOAD_DIR") or settings.upload_dir, exist_ok=True)
    _auto_seed()
    yield


app = FastAPI(title="CollabZ API", lifespan=lifespan)
register_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _include_modules() -> None:
    import app.modules as modules_pkg

    base = list(modules_pkg.__path__)[0]
    for info in sorted(pkgutil.iter_modules(modules_pkg.__path__), key=lambda m: m.name):
        if not info.ispkg:
            continue
        if "router" not in {m.name for m in pkgutil.iter_modules([os.path.join(base, info.name)])}:
            continue
        try:
            mod = importlib.import_module(f"app.modules.{info.name}.router")
            router = getattr(mod, "router", None)
            if router is None:
                continue
            app.include_router(router)
            log.info("Included router: app.modules.%s", info.name)
        except Exception:
            log.error("Failed to import router for module %s:\n%s", info.name, traceback.format_exc())


_include_modules()


@app.get("/health")
def health():
    return {"status": "ok"}
