"""
metrics.py
----------
Computes the top-bar "PyTorch LSTM ADE / FDE" numbers by aggregating the
per-object trajectory predictor's leave-one-out error across a sample of
tracked instances from the loaded scenes. Cached after first computation
since nuScenes-mini is small but this still touches every scene once.
"""
from __future__ import annotations

import functools

import numpy as np

from . import nuscenes_loader
from .trajectory_model import predict_trajectories_batch

MAX_INSTANCES_SAMPLED = 40


@functools.lru_cache(maxsize=1)
def compute_dataset_metrics() -> dict:
    nusc = nuscenes_loader.get_nusc()

    histories: dict[str, list] = {}

    for scene in nusc.scene:
        if len(histories) >= MAX_INSTANCES_SAMPLED:
            break
        samples = nuscenes_loader.list_samples_for_scene(scene["token"])
        if not samples:
            continue
        mid_sample = samples[len(samples) // 2]["token"]
        sample = nusc.get("sample", mid_sample)

        for ann_token in sample["anns"]:
            if len(histories) >= MAX_INSTANCES_SAMPLED:
                break
            ann = nusc.get("sample_annotation", ann_token)
            history = nuscenes_loader.get_instance_history(ann["instance_token"], mid_sample)
            if len(history) < 3:
                continue
            histories[ann["instance_token"]] = history

    if not histories:
        return {"ade_meters": 0.0, "fde_meters": 0.0, "instances_evaluated": 0}

    results = predict_trajectories_batch(histories)
    ade_list = [r["ade_meters"] for r in results.values()]
    fde_list = [r["fde_meters"] for r in results.values()]

    return {
        "ade_meters": round(float(np.mean(ade_list)), 2),
        "fde_meters": round(float(np.mean(fde_list)), 2),
        "instances_evaluated": len(histories),
    }
