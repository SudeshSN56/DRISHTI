from __future__ import annotations

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from core.config import OUTPUTS_DIR

router = APIRouter(prefix="/api/runs", tags=["files"])


@router.get("/{run_id}/files/{file_path:path}")
def get_run_file(run_id: str, file_path: str):
    run_dir = (OUTPUTS_DIR / run_id).resolve()
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run not found")

    target_file = (run_dir / file_path).resolve()
    # Security check: prevent path traversal outside run_dir
    try:
        target_file.relative_to(run_dir)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if not target_file.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    suffix = target_file.suffix.lower()
    media_types = {
        ".mp4": "video/mp4",
        ".csv": "text/csv",
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(
        path=str(target_file),
        media_type=media_type,
        filename=target_file.name,
    )
