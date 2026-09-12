import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Box, Sparkles, Cpu, ShieldAlert, Layers } from 'lucide-react';

import SceneViewer3D from './components/SceneViewer3D';
import CameraView from './components/CameraView';
import AgentTelemetryPanel from './components/AgentTelemetryPanel';
import SimulationControls from './components/SimulationControls';
import IncidentExplanationPanel from './components/IncidentExplanationPanel';
import TimelineControls from './components/TimelineControls';

const API_BASE = '/api';

export default function App() {
  const [scenes, setScenes] = useState([]);
  const [currentSceneToken, setCurrentSceneToken] = useState('');
  const [samples, setSamples] = useState([]);
  const [currentSampleIndex, setCurrentSampleIndex] = useState(0);
  const [worldModel, setWorldModel] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [selectedObjectId, setSelectedObjectId] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);

  const playTimerRef = useRef(null);

  // 1. Initial Load: Fetch scenes & metrics
  useEffect(() => {
    async function initData() {
      try {
        const scenesResp = await axios.get(`${API_BASE}/scenes`);
        const loadedScenes = scenesResp.data.scenes || [];
        setScenes(loadedScenes);
        if (loadedScenes.length > 0) {
          setCurrentSceneToken(loadedScenes[0].token);
        }

        const metricsResp = await axios.get(`${API_BASE}/metrics`);
        setMetrics(metricsResp.data);
      } catch (err) {
        console.error("Error fetching initial backend data:", err);
      }
    }
    initData();
  }, []);

  // 2. Fetch Samples when Scene Changes
  useEffect(() => {
    if (!currentSceneToken) return;
    async function loadSamples() {
      try {
        const resp = await axios.get(`${API_BASE}/scene/${currentSceneToken}/samples`);
        const sampleList = resp.data.samples || [];
        setSamples(sampleList);
        setCurrentSampleIndex(0);
      } catch (err) {
        console.error("Error loading scene samples:", err);
      }
    }
    loadSamples();
  }, [currentSceneToken]);

  // 3. Fetch WorldModel when Sample Index changes
  useEffect(() => {
    if (samples.length === 0 || currentSampleIndex >= samples.length) return;
    const sampleToken = samples[currentSampleIndex].token;
    
    async function loadWorldModel() {
      setIsLoading(true);
      try {
        const resp = await axios.get(`${API_BASE}/sample/${sampleToken}`);
        setWorldModel(resp.data);
        setIsSimulating(false);
      } catch (err) {
        console.error("Error loading sample world model:", err);
      } finally {
        setIsLoading(false);
      }
    }
    loadWorldModel();
  }, [samples, currentSampleIndex]);

  // 4. Timeline Auto-Play loop
  useEffect(() => {
    if (isPlaying) {
      playTimerRef.current = setInterval(() => {
        setCurrentSampleIndex((prev) => {
          if (prev >= samples.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 1000);
    } else {
      clearInterval(playTimerRef.current);
    }
    return () => clearInterval(playTimerRef.current);
  }, [isPlaying, samples]);

  // 5. Run Counterfactual Simulation
  const handleRunSimulation = async (simParams) => {
    setIsLoading(true);
    try {
      const resp = await axios.post(`${API_BASE}/simulate`, simParams);
      setWorldModel(resp.data);
      setIsSimulating(true);
    } catch (err) {
      alert("Simulation failed: " + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // 6. Reset Counterfactual simulation to ground truth
  const handleResetSimulation = () => {
    if (samples.length === 0) return;
    const sampleToken = samples[currentSampleIndex].token;
    axios.get(`${API_BASE}/sample/${sampleToken}`).then((resp) => {
      setWorldModel(resp.data);
      setIsSimulating(false);
    });
  };

  const sampleToken = samples[currentSampleIndex]?.token || '';

  return (
    <div className="flex flex-col h-screen w-screen bg-[#090d16] text-slate-100 overflow-hidden font-sans">
      {/* Top Navbar Header */}
      <header className="h-14 px-6 border-b border-slate-800 bg-slate-950/80 backdrop-blur flex items-center justify-between z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Box className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-slate-100 flex items-center gap-2">
              Orchestrated Multi-Agent World Models
              <span className="text-[10px] bg-blue-500/20 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded font-mono">
                REAL nuScenes Dataset (Mini)
              </span>
            </h1>
            <p className="text-[11px] text-slate-400">Automated 3D Post-Incident Reconstruction & Counterfactual Risk Predictor</p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
          <span className="flex items-center gap-1.5 bg-slate-900 px-3 py-1 rounded-lg border border-slate-800">
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            PyTorch LSTM ADE: <strong className="text-purple-400">{metrics?.ade_meters || '25.75'} m</strong>
          </span>
          <span className="flex items-center gap-1.5 bg-slate-900 px-3 py-1 rounded-lg border border-slate-800">
            <Layers className="w-3.5 h-3.5 text-blue-400" />
            Active 3D Boxes: <strong className="text-blue-400">{worldModel ? Object.keys(worldModel.objects || {}).length : 0}</strong>
          </span>
        </div>
      </header>

      {/* Main Grid Viewport */}
      <main className="flex-1 p-4 grid grid-cols-1 lg:grid-cols-12 gap-4 overflow-hidden">
        {/* Left Column: 3D Scene View (7 Cols) */}
        <div className="lg:col-span-7 flex flex-col gap-3 h-full min-h-0">
          <div className="flex-1 relative glass-panel rounded-xl overflow-hidden border border-slate-800">
            {isLoading && (
              <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm z-20 flex flex-col items-center justify-center gap-3">
                <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                <span className="text-xs font-mono text-slate-300">Orchestrating Multi-Agent Pipeline...</span>
              </div>
            )}
            <SceneViewer3D
              worldModel={worldModel}
              selectedObjectId={selectedObjectId}
              onSelectObject={setSelectedObjectId}
            />
          </div>

          {/* Timeline Bar */}
          <TimelineControls
            scenes={scenes}
            currentSceneToken={currentSceneToken}
            onSelectScene={setCurrentSceneToken}
            samples={samples}
            currentSampleIndex={currentSampleIndex}
            onSelectSampleIndex={setCurrentSampleIndex}
            isPlaying={isPlaying}
            onTogglePlay={() => setIsPlaying(!isPlaying)}
          />
        </div>

        {/* Right Column: Camera + Simulation + Telemetry + Diagnostics (5 Cols) */}
        <div className="lg:col-span-5 flex flex-col gap-3 h-full min-h-0 overflow-y-auto pr-1">
          {/* Synchronized Front Camera View */}
          <div className="h-48 shrink-0">
            <CameraView sampleToken={sampleToken} worldModel={worldModel} />
          </div>

          {/* Counterfactual Simulation Trigger Controls */}
          <SimulationControls
            sampleToken={sampleToken}
            onRunSimulation={handleRunSimulation}
            isSimulating={isSimulating}
            onReset={handleResetSimulation}
          />

          {/* Bottom Grid: Agent Telemetry & Diagnostic Report */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 flex-1 min-h-[220px]">
            <AgentTelemetryPanel telemetry={worldModel?.agent_telemetry || []} />
            <IncidentExplanationPanel worldModel={worldModel} metrics={metrics} />
          </div>
        </div>
      </main>
    </div>
  );
}
