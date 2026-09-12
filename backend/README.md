# Backend — Orchestrated Multi-Agent World Models

FastAPI service that loads the real **nuScenes-mini** dataset via
[`nuscenes-devkit`](https://github.com/nutonomy/nuscenes-devkit), runs it through
a small multi-agent pipeline (detection → tracking → PyTorch LSTM trajectory
prediction → risk assessment → explanation), and serves the exact API the
React frontend in `../src` already expects.

## 1. Get the nuScenes-mini dataset (you have to do this part yourself)

nuScenes requires free registration and can't be downloaded anonymously or
scripted without your credentials, so there's no way to bundle it for you.

1. Go to https://www.nuscenes.org/download and create a free account.
2. Download **"Mini" (v1.0-mini, ~4GB)** — *not* the full trainval set.
3. Extract it so you end up with this layout:

   ```
   backend/data/nuscenes/
     maps/
     samples/
     sweeps/
     v1.0-mini/
   ```

   You can put it anywhere — just point `NUSCENES_DATAROOT` at it (see below).

## 2. Install dependencies

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`nuscenes-devkit` pulls in numpy, opencv, shapely, pyquaternion, etc.
`torch` here is the CPU build; swap in a CUDA build from
https://pytorch.org/get-started/locally/ if you have a GPU and want it,
but it isn't required — the LSTM here is tiny.

## 3. Point the backend at your dataset

```bash
export NUSCENES_DATAROOT=/absolute/path/to/backend/data/nuscenes   # default: ./data/nuscenes
export NUSCENES_VERSION=v1.0-mini                                   # default, leave as-is for mini
```

(On Windows: `set NUSCENES_DATAROOT=...`)

## 4. Run it

```bash
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/api/health — it should report
`{"status": "ok", "dataset_ready": true}`. If `dataset_ready` is `false`,
the error from every other endpoint will tell you exactly what's missing
(wrong path, missing devkit, wrong dataset version, etc.) — the backend
never silently falls back to fake data.

Then run the frontend as usual (`npm install && npm run dev` in the repo
root) — it already points at `http://localhost:8000/api`.

## API surface

| Method | Path                              | Notes |
|--------|------------------------------------|-------|
| GET    | `/api/health`                     | dataset readiness check |
| GET    | `/api/scenes`                     | all nuScenes-mini scenes |
| GET    | `/api/metrics`                    | dataset-wide LSTM ADE/FDE |
| GET    | `/api/scene/{scene_token}/samples`| keyframes in a scene |
| GET    | `/api/sample/{sample_token}`      | full world model (objects, risk, telemetry, narrative) |
| POST   | `/api/simulate`                   | counterfactual re-run (speed surge / brake failure / cut-in) |
| GET    | `/api/camera-image/{sample_token}`| CAM_FRONT JPEG for that keyframe |
| POST   | `/api/export-report`              | renders a world model into a PDF |

## Notes on the "PyTorch LSTM" / ADE / FDE numbers

nuScenes-mini only has 10 scenes, which is nowhere near enough to pretrain a
real motion-forecasting model from scratch and have the number mean anything
across restarts. So instead of hardcoding a plausible-looking ADE/FDE, this
backend trains a small `nn.LSTM` seq2seq model **on the fly**, per request,
on each object's own recent motion history (see `app/trajectory_model.py`),
and reports genuine leave-one-out displacement error. It's an honest, if
modest, forecaster — swap in a checkpoint trained on the full nuScenes
prediction challenge if you want materially better numbers; the surrounding
API/agent pipeline won't need to change.

## Troubleshooting

- **"nuScenes dataroot not found"** — check `NUSCENES_DATAROOT` points at the
  folder *containing* `maps/`, `samples/`, `sweeps/`, `v1.0-mini/`, not one
  level up or down from it.
- **"Failed to load nuScenes dataset... Underlying error: ..."** — usually
  means you extracted the full trainval set instead of mini, or the zip was
  only partially extracted. Re-check file sizes against nuScenes' download
  page.
- **CORS errors in the browser** — the backend only allows
  `http://localhost:5173` / `127.0.0.1:5173` (Vite's default) by default;
  edit `allow_origins` in `app/main.py` if you're running the frontend
  elsewhere.
- **Slow first request per sample** — each `/api/sample/*` and `/api/simulate`
  call trains a fresh tiny LSTM for that keyframe's objects (~1-2s for a busy
  scene). That's expected; it's not loading anything from disk repeatedly.
