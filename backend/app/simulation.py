"""
simulation.py
--------------
Counterfactual "what if" scenarios requested from SimulationControls.jsx.
Each scenario re-runs the same agent pipeline used for ground truth, but
perturbs the prediction stage's inputs so the resulting forecast reflects
the hypothetical (e.g. a target vehicle suddenly moving 2.5x faster).

This is intentionally a re-run of the real pipeline (not a hand-authored
fake payload) so the 3D viewer, telemetry panel, and explanation panel all
stay internally consistent with whatever scenario was requested.
"""
from __future__ import annotations

from .agents import run_pipeline

SCENARIOS = {
    "SPEED_SURGE": "Target Speed Surge",
    "EMERGENCY_BRAKE_FAILURE": "Sudden Brake Failure",
    "LANE_DRIFT_CUT_IN": "Aggressive Lane Drift Cut-In",
}


def run_simulation(sample_token: str, scenario_type: str, speed_multiplier: float, scenario_name: str | None) -> dict:
    label = scenario_name or SCENARIOS.get(scenario_type, scenario_type)

    if scenario_type == "EMERGENCY_BRAKE_FAILURE":
        # Brake failure: ego closing distance faster than expected is
        # modeled as an *increase* in relative approach speed for the
        # nearest lead object, same as a speed surge from the ego's frame.
        effective_multiplier = max(speed_multiplier, 1.6)
    elif scenario_type == "LANE_DRIFT_CUT_IN":
        # A cut-in mainly changes lateral trajectory, but since our forecaster
        # only sees speed, model it as a moderate multiplier that pulls the
        # projected path closer to ego faster.
        effective_multiplier = max(speed_multiplier * 0.8, 1.2)
    else:  # SPEED_SURGE or unknown -> take the requested multiplier as-is
        effective_multiplier = speed_multiplier

    world_model = run_pipeline(sample_token, speed_multiplier=effective_multiplier, scenario_name=label)
    world_model["simulation"] = {
        "scenario_type": scenario_type,
        "scenario_name": label,
        "speed_multiplier": speed_multiplier,
        "effective_multiplier": effective_multiplier,
    }
    return world_model
