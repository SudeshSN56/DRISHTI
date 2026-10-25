from __future__ import annotations

import asyncio
from fastapi import APIRouter, HTTPException

from core.config import OUTPUTS_DIR
from core.report import build_brief
from api.schemas import BriefResponse

router = APIRouter(prefix="/api/runs", tags=["report"])


@router.post("/{run_id}/brief", response_model=BriefResponse)
async def generate_brief(run_id: str) -> BriefResponse:
    run_dir = OUTPUTS_DIR / run_id
    if not run_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    csv_path = run_dir / "detections.csv"
    if not csv_path.is_file():
        raise HTTPException(status_code=404, detail=f"Detections CSV not found for run: {run_id}")

    try:
        # Run report generation in thread pool to not block async loop
        pdf_path = await asyncio.to_thread(build_brief, csv_path)
        return BriefResponse(
            status="ok",
            path=f"/api/runs/{run_id}/files/brief.pdf",
            filename=pdf_path.name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate brief PDF: {e}")
