import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .config import get_settings
from .database import ensure_schema
from .routers import auth, reviews, stats

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Simple schema bootstrap for development. Use Alembic migrations once the schema stabilises.
    ensure_schema()
    yield


app = FastAPI(title="WizForge AI", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(reviews.router)
app.include_router(stats.router)


@app.get("/", include_in_schema=False)
def root():
    # the UI lives on the Vite dev server; the backend root points at the API docs
    return RedirectResponse("/docs")


@app.get("/api/health", tags=["meta"])
def health():
    s = get_settings()
    return {"status": "ok", "ai_enabled": s.ai_enabled, "ai_configured": s.ai_configured, "ai_model": s.ai_model}
