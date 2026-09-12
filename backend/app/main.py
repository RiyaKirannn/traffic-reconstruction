"""
main.py
-------
FastAPI backend for the Orchestrated Multi-Agent World Models frontend.
Implements exactly the endpoints the React app already calls
(see src/App.jsx, src/components/CameraView.jsx and
src/components/IncidentExplanationPanel.jsx):

    GET  /api/scenes
    GET  /api/metrics
    GET  /api/scene/{scene_token}/samples
    GET  /api/sample/{sample_token}
    POST /api/simulate
    GET  /api/camera-image/{sample_token}
    POST /api/export-report

Run with:
    uvicorn app.main:app --reload --port 8000
(from inside backend/, with NUSCENES_DATAROOT pointing at your extracted
nuScenes-mini folder — see backend/README.md)
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from . import metrics, nuscenes_loader, simulation
from .agents import run_pipeline

app = FastAPI(title="Traffic Reconstruction Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulateRequest(BaseModel):
    sample_token: str
    scenario_type: str = "SPEED_SURGE"
    speed_multiplier: float = 2.0
    scenario_name: str | None = None


class ExportReportRequest(BaseModel):
    world_model: dict


def _require_dataset():
    if not nuscenes_loader.is_dataset_ready():
        raise HTTPException(
            status_code=503,
            detail=(
                "nuScenes-mini dataset not found. Set NUSCENES_DATAROOT to your "
                "extracted dataset folder and restart the backend. See backend/README.md."
            ),
        )


@app.get("/api/health")
def health():
    return {"status": "ok", "dataset_ready": nuscenes_loader.is_dataset_ready()}


@app.get("/api/scenes")
def get_scenes():
    _require_dataset()
    try:
        return {"scenes": nuscenes_loader.list_scenes()}
    except nuscenes_loader.NuScenesUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/metrics")
def get_metrics():
    _require_dataset()
    try:
        return metrics.compute_dataset_metrics()
    except nuscenes_loader.NuScenesUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/scene/{scene_token}/samples")
def get_scene_samples(scene_token: str):
    _require_dataset()
    try:
        return {"samples": nuscenes_loader.list_samples_for_scene(scene_token)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown scene token: {scene_token}") from exc


@app.get("/api/sample/{sample_token}")
def get_sample(sample_token: str):
    _require_dataset()
    try:
        return run_pipeline(sample_token)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown sample token: {sample_token}") from exc


@app.post("/api/simulate")
def post_simulate(req: SimulateRequest):
    _require_dataset()
    try:
        return simulation.run_simulation(
            req.sample_token, req.scenario_type, req.speed_multiplier, req.scenario_name
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown sample token: {req.sample_token}") from exc


@app.get("/api/camera-image/{sample_token}")
def get_camera_image(sample_token: str, channel: str = Query(default="CAM_FRONT")):
    _require_dataset()
    try:
        path = nuscenes_loader.get_camera_image_path(sample_token, channel=channel)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Image file missing on disk: {path}")
    return FileResponse(path, media_type="image/jpeg")


@app.post("/api/export-report")
def post_export_report(req: ExportReportRequest):
    from .report import build_report_pdf

    pdf_bytes = build_report_pdf(req.world_model)
    token = req.world_model.get("sample_token", "report")[:8]
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Incident_Reconstruction_Report_{token}.pdf"},
    )
