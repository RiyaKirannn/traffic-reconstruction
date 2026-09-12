"""
agents.py
---------
The "multi-agent pipeline" the UI visualizes in AgentTelemetryPanel. Each
agent is a small, single-responsibility function; `run_pipeline` orchestrates
them in sequence, times each one, and collects per-agent telemetry plus any
failures (so a broken agent shows up as a red ⚠ card instead of a 500).

Pipeline stages:
  1. DetectionAgent          - loads annotated 3D boxes for the sample
  2. TrackingAgent           - pulls each object's recent position history
  3. PredictionAgent         - runs the PyTorch LSTM forecaster per object
  4. RiskAssessmentAgent     - scores collision/proximity risk per object + pairwise interactions
  5. ExplanationAgent        - turns the above into a narrative incident report
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from . import nuscenes_loader
from .trajectory_model import predict_trajectories_batch

EGO_RADIUS_M = 1.5
PROXIMITY_CRITICAL_M = 4.0
PROXIMITY_HIGH_M = 8.0


@dataclass
class AgentResult:
    agent_name: str
    status: str
    execution_time_ms: float
    summary: str
    data: dict[str, Any] = field(default_factory=dict)


def _timed(agent_name: str, fn: Callable[[], tuple[dict, str]]) -> tuple[AgentResult, dict]:
    start = time.perf_counter()
    try:
        data, summary = fn()
        elapsed = (time.perf_counter() - start) * 1000
        return AgentResult(agent_name, "SUCCESS", round(elapsed, 2), summary, data), data
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return AgentResult(agent_name, "ERROR", round(elapsed, 2), f"{type(exc).__name__}: {exc}", {}), {}


def _detection_agent(sample_token: str) -> tuple[dict, str]:
    world_model = nuscenes_loader.get_world_model(sample_token)
    n = len(world_model["objects"])
    return {"world_model": world_model}, f"Loaded {n} annotated 3D boxes from LIDAR_TOP keyframe."


def _tracking_agent(sample_token: str, objects: dict) -> tuple[dict, str]:
    histories = {}
    for instance_token in objects:
        histories[instance_token] = nuscenes_loader.get_instance_history(instance_token, sample_token)
    tracked = sum(1 for h in histories.values() if len(h) >= 2)
    return {"histories": histories}, f"Recovered motion history for {tracked}/{len(objects)} tracked instances."


def _prediction_agent(histories: dict, speed_multiplier: float) -> tuple[dict, str]:
    multipliers = {instance_token: speed_multiplier for instance_token in histories}
    predictions = predict_trajectories_batch(histories, multipliers)
    ade_list = [p["ade_meters"] for p in predictions.values()]
    fde_list = [p["fde_meters"] for p in predictions.values()]
    avg_ade = round(float(np.mean(ade_list)), 2) if ade_list else 0.0
    avg_fde = round(float(np.mean(fde_list)), 2) if fde_list else 0.0
    return (
        {"predictions": predictions, "avg_ade": avg_ade, "avg_fde": avg_fde},
        f"PyTorch LSTM forecast {len(predictions)} trajectories (batch ADE {avg_ade}m / FDE {avg_fde}m).",
    )


def _risk_assessment_agent(objects: dict, predictions: dict) -> tuple[dict, str]:
    interactions = []
    scored_objects = {}
    critical_count = 0

    for instance_token, obj in objects.items():
        pos = np.array(obj["position"][:2])
        dist_to_ego = float(np.linalg.norm(pos))
        pred = predictions.get(instance_token, {})
        traj = pred.get("predicted_trajectory", [])
        min_future_dist = min(
            (float(np.linalg.norm(np.array(pt) - np.array([0.0, 0.0]))) for pt in traj),
            default=dist_to_ego,
        )
        closest_approach = min(dist_to_ego, min_future_dist)

        if closest_approach < PROXIMITY_CRITICAL_M:
            risk_score = min(1.0, 1.0 - (closest_approach / PROXIMITY_CRITICAL_M) * 0.3)
            risk_level = "CRITICAL"
            critical_count += 1
        elif closest_approach < PROXIMITY_HIGH_M:
            risk_score = 0.4 + 0.4 * (1 - (closest_approach - PROXIMITY_CRITICAL_M) / (PROXIMITY_HIGH_M - PROXIMITY_CRITICAL_M))
            risk_level = "HIGH"
        else:
            risk_score = max(0.0, 0.4 * (1 - (closest_approach - PROXIMITY_HIGH_M) / 20.0))
            risk_level = "LOW"

        scored_objects[instance_token] = {
            **obj,
            "risk_score": round(float(risk_score), 3),
            "risk_level": risk_level,
            "predicted_trajectory": traj,
            "closest_approach_m": round(closest_approach, 2),
        }

        if risk_level in ("CRITICAL", "HIGH"):
            interactions.append(
                {
                    "object_id": instance_token,
                    "category": obj["category"],
                    "risk_level": risk_level,
                    "closest_approach_m": round(closest_approach, 2),
                    "description": (
                        f"{obj['category'].split('.')[-1]} projected within "
                        f"{round(closest_approach, 1)}m of ego vehicle."
                    ),
                }
            )

    interactions.sort(key=lambda i: i["closest_approach_m"])
    return (
        {"objects": scored_objects, "interactions": interactions, "critical_count": critical_count},
        f"Flagged {len(interactions)} elevated-risk interactions ({critical_count} critical) "
        f"across {len(scored_objects)} tracked objects.",
    )


def _explanation_agent(interactions: list, critical_count: int, avg_ade: float, avg_fde: float, scenario_name: str | None) -> tuple[dict, str]:
    scenario_prefix = f"Counterfactual scenario '{scenario_name}': " if scenario_name else ""

    if critical_count > 0:
        risk_level = "CRITICAL"
        top = interactions[0]
        title = f"Imminent Collision Risk: {top['category'].split('.')[-1].title()}"
        narrative = (
            f"{scenario_prefix}"
            f"The multi-agent pipeline projects a critical proximity event with a "
            f"{top['category'].split('.')[-1]} closing to within {top['closest_approach_m']}m of the "
            f"ego vehicle. Trajectory forecasting carries an average displacement error of "
            f"{avg_ade}m (final-step error {avg_fde}m), so this projection should be read as an "
            f"early-warning signal rather than a certainty — but it warrants immediate evasive "
            f"planning in a real deployment."
        )
    elif interactions:
        risk_level = "HIGH"
        top = interactions[0]
        title = f"Elevated Risk: {top['category'].split('.')[-1].title()} Proximity"
        narrative = (
            f"{scenario_prefix}"
            f"No critical collisions are projected, but a {top['category'].split('.')[-1]} is forecast "
            f"to approach within {top['closest_approach_m']}m of the ego vehicle, which is close enough "
            f"to merit increased following distance or a speed reduction."
        )
    else:
        risk_level = "LOW"
        title = "Nominal Scene: No Elevated Risk Detected"
        narrative = (
            f"{scenario_prefix}"
            f"All tracked objects are forecast to remain clear of the ego vehicle's projected path. "
            f"No corrective action indicated by the current motion forecast."
        )

    causality_breakdown = [
        {"factor": "Peak Risk Score", "value": f"{max((i['closest_approach_m'] for i in interactions), default=0)}", "impact": risk_level},
        {"factor": "Critical Interactions", "value": str(critical_count), "impact": "CRITICAL" if critical_count else "LOW"},
        {"factor": "Trajectory Forecast ADE", "value": f"{avg_ade} m", "impact": "HIGH" if avg_ade > 5 else "LOW"},
        {"factor": "Trajectory Forecast FDE", "value": f"{avg_fde} m", "impact": "HIGH" if avg_fde > 8 else "LOW"},
    ]

    explanation = {
        "risk_level": risk_level,
        "title": title,
        "narrative": narrative,
        "causality_breakdown": causality_breakdown,
    }
    return {"incident_explanation": explanation}, f"Generated {risk_level.lower()}-risk incident narrative."


def run_pipeline(sample_token: str, speed_multiplier: float = 1.0, scenario_name: str | None = None) -> dict[str, Any]:
    """
    Runs the full detection -> tracking -> prediction -> risk -> explanation
    pipeline for a single sample and returns the API-ready world model plus
    agent telemetry.
    """
    telemetry: list[AgentResult] = []

    result, data = _timed("DetectionAgent", lambda: _detection_agent(sample_token))
    telemetry.append(result)
    world_model = data.get("world_model", {"sample_token": sample_token, "objects": {}})
    objects = world_model.get("objects", {})

    result, data = _timed("TrackingAgent", lambda: _tracking_agent(sample_token, objects))
    telemetry.append(result)
    histories = data.get("histories", {})

    result, data = _timed("PredictionAgent", lambda: _prediction_agent(histories, speed_multiplier))
    telemetry.append(result)
    predictions = data.get("predictions", {})
    avg_ade = data.get("avg_ade", 0.0)
    avg_fde = data.get("avg_fde", 0.0)

    result, data = _timed("RiskAssessmentAgent", lambda: _risk_assessment_agent(objects, predictions))
    telemetry.append(result)
    scored_objects = data.get("objects", objects)
    interactions = data.get("interactions", [])
    critical_count = data.get("critical_count", 0)

    result, data = _timed(
        "ExplanationAgent",
        lambda: _explanation_agent(interactions, critical_count, avg_ade, avg_fde, scenario_name),
    )
    telemetry.append(result)
    incident_explanation = data.get("incident_explanation", {})

    world_model["objects"] = scored_objects
    world_model["interactions"] = interactions
    world_model["incident_explanation"] = incident_explanation
    world_model["agent_telemetry"] = [
        {
            "agent_name": t.agent_name,
            "status": t.status,
            "execution_time_ms": t.execution_time_ms,
            "summary": t.summary,
        }
        for t in telemetry
    ]
    world_model["prediction_metrics"] = {"ade_meters": avg_ade, "fde_meters": avg_fde}
    return world_model
