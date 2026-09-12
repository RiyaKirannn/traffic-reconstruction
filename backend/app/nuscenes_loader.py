"""
nuscenes_loader.py
-------------------
Thin, defensive wrapper around `nuscenes-devkit` that loads the nuScenes-mini
split and exposes the pieces of it this app actually needs: scenes, sample
(keyframe) lists, per-sample annotated 3D boxes, ego pose, and camera images.

This module is deliberately isolated from FastAPI so it can be unit tested
or swapped out without touching the API layer.
"""
from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Any

import numpy as np
from pyquaternion import Quaternion

_DEFAULT_DATAROOT = Path(__file__).resolve().parents[1] / "data" / "nuscenes"
DATAROOT = os.environ.get("NUSCENES_DATAROOT") or str(_DEFAULT_DATAROOT)
VERSION = os.environ.get("NUSCENES_VERSION", "v1.0-mini")


class NuScenesUnavailableError(RuntimeError):
    """Raised when the nuScenes-mini dataset isn't present/loadable."""


@functools.lru_cache(maxsize=1)
def get_nusc():
    """
    Lazily load and cache the NuScenes object. Raises a clear,
    actionable error instead of a deep stack trace if the dataset
    (or the devkit itself) isn't available.
    """
    dataroot = Path(DATAROOT)
    if not dataroot.exists():
        raise NuScenesUnavailableError(
            f"nuScenes dataroot not found at '{dataroot.resolve()}'. "
            f"Download nuScenes-mini from https://www.nuscenes.org/download "
            f"(free registration required) and extract it there, or set the "
            f"NUSCENES_DATAROOT environment variable to point at it. "
            f"See backend/README.md for the exact steps."
        )
    try:
        from nuscenes.nuscenes import NuScenes
    except ImportError as exc:  # pragma: no cover
        raise NuScenesUnavailableError(
            "nuscenes-devkit is not installed. Run `pip install -r requirements.txt` "
            "inside backend/."
        ) from exc

    try:
        return NuScenes(version=VERSION, dataroot=str(dataroot), verbose=False)
    except Exception as exc:
        raise NuScenesUnavailableError(
            f"Failed to load nuScenes dataset at '{dataroot}' (version={VERSION}). "
            f"Make sure you extracted the mini split (not the full/trainval split) "
            f"and that the folder contains 'maps/', 'samples/', 'sweeps/', and "
            f"'v1.0-mini/'. Underlying error: {exc}"
        ) from exc


def is_dataset_ready() -> bool:
    try:
        get_nusc()
        return True
    except NuScenesUnavailableError:
        return False


def list_scenes() -> list[dict[str, Any]]:
    nusc = get_nusc()
    return [
        {
            "token": s["token"],
            "name": s["name"],
            "description": s["description"] or s["name"],
            "nbr_samples": s["nbr_samples"],
        }
        for s in nusc.scene
    ]


def list_samples_for_scene(scene_token: str) -> list[dict[str, Any]]:
    nusc = get_nusc()
    scene = nusc.get("scene", scene_token)
    samples = []
    sample_token = scene["first_sample_token"]
    idx = 0
    while sample_token:
        sample = nusc.get("sample", sample_token)
        samples.append({"token": sample_token, "index": idx, "timestamp": sample["timestamp"]})
        sample_token = sample["next"]
        idx += 1
    return samples


def _category_short(name: str) -> str:
    # nuScenes categories look like "vehicle.car", "human.pedestrian.adult"
    return name


def get_ego_pose_for_sample(nusc, sample: dict) -> dict:
    lidar_data = nusc.get("sample_data", sample["data"]["LIDAR_TOP"])
    ego_pose = nusc.get("ego_pose", lidar_data["ego_pose_token"])
    return ego_pose


def get_world_model(sample_token: str) -> dict[str, Any]:
    """
    Build the "world model" the frontend expects for a single sample
    (keyframe): every annotated 3D box, converted into ego-vehicle-relative
    coordinates so the 3D viewer can place them around the ego at the origin.
    """
    nusc = get_nusc()
    sample = nusc.get("sample", sample_token)
    ego_pose = get_ego_pose_for_sample(nusc, sample)
    ego_translation = np.array(ego_pose["translation"])
    ego_rotation_inv = Quaternion(ego_pose["rotation"]).inverse

    objects: dict[str, Any] = {}
    for ann_token in sample["anns"]:
        ann = nusc.get("sample_annotation", ann_token)

        # World -> ego-relative translation
        rel = np.array(ann["translation"]) - ego_translation
        rel_ego = ego_rotation_inv.rotate(rel)

        objects[ann["instance_token"]] = {
            "id": ann["instance_token"],
            "category": _category_short(ann["category_name"]),
            "position": [float(rel_ego[0]), float(rel_ego[1]), float(rel_ego[2])],
            "size": [float(ann["size"][1]), float(ann["size"][0]), float(ann["size"][2])],
            "rotation": list(ann["rotation"]),
            "num_lidar_pts": ann["num_lidar_pts"],
            "visibility_token": ann.get("visibility_token"),
            "attribute_tokens": ann.get("attribute_tokens", []),
        }

    return {
        "sample_token": sample_token,
        "timestamp": sample["timestamp"],
        "scene_token": sample["scene_token"],
        "ego_pose": {
            "translation": ego_pose["translation"],
            "rotation": ego_pose["rotation"],
        },
        "objects": objects,
    }


def get_instance_history(instance_token: str, up_to_sample_token: str, max_len: int = 6) -> list[list[float]]:
    """
    Walk backwards through an instance's annotations (in ego-relative XY)
    up to (and including) the given sample, for use as trajectory-predictor
    input. Returns oldest -> newest.
    """
    nusc = get_nusc()
    instance = nusc.get("instance", instance_token)
    ann_token = instance["first_annotation_token"]

    history = []
    while ann_token:
        ann = nusc.get("sample_annotation", ann_token)
        sample = nusc.get("sample", ann["sample_token"])
        ego_pose = get_ego_pose_for_sample(nusc, sample)
        ego_translation = np.array(ego_pose["translation"])
        ego_rotation_inv = Quaternion(ego_pose["rotation"]).inverse
        rel = ego_rotation_inv.rotate(np.array(ann["translation"]) - ego_translation)
        history.append({"sample_token": ann["sample_token"], "xy": [float(rel[0]), float(rel[1])]})

        if ann["sample_token"] == up_to_sample_token:
            break
        ann_token = ann["next"]

    trimmed = history[-max_len:]
    return [h["xy"] for h in trimmed]


def get_camera_image_path(sample_token: str, channel: str = "CAM_FRONT") -> Path:
    nusc = get_nusc()
    sample = nusc.get("sample", sample_token)
    if channel not in sample["data"]:
        raise KeyError(f"Channel '{channel}' not present in sample {sample_token}")
    cam_data = nusc.get("sample_data", sample["data"][channel])
    return Path(nusc.dataroot) / cam_data["filename"]
