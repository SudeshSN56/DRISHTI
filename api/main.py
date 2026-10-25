from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import PROJECT_ROOT
from api.routes import detect, files, meta, report, runs

app = FastAPI(
    title="DRISHTI · Aerial Intelligence API",
    description="FastAPI backend for DRISHTI drone video object detection, tracking, and tactical reporting.",
    version="2.0.0",
)

# CORS configuration for Vite dev server and external clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(meta.router)
app.include_router(runs.router)
app.include_router(files.router)
app.include_router(report.router)
app.include_router(detect.router)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": "DRISHTI API"}


# Serve built React frontend in production if dist directory exists
WEB_DIST_DIR = PROJECT_ROOT / "web" / "dist"
if WEB_DIST_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIST_DIR), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
