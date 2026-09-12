# Traffic Reconstruction — Orchestrated Multi-Agent World Models

Full-stack app: React/Vite/Three.js frontend + FastAPI backend, reconstructing
and visualizing real **nuScenes-mini** driving scenes in 3D, with a small
multi-agent pipeline (detection → tracking → PyTorch LSTM prediction → risk
assessment → explanation) and counterfactual "what if" incident simulation.

## Quick start

**Backend** (see `backend/README.md` for full details, including how to get
the nuScenes-mini dataset — it requires free registration on nuscenes.org so
it can't be bundled here):

```bash
cd backend
pip install -r requirements.txt
export NUSCENES_DATAROOT=/path/to/extracted/nuscenes-mini
uvicorn app.main:app --reload --port 8000
```

**Frontend:**

```bash
npm install
npm run dev
```

Then open the printed Vite URL (default http://localhost:5173). The frontend
calls the backend at `http://localhost:8000/api`.

---

## Frontend template details



This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.
