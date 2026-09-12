import React, { useState } from 'react';
import { Sliders, Zap, AlertTriangle, Play, RefreshCw } from 'lucide-react';

export default function SimulationControls({ sampleToken, onRunSimulation, isSimulating, onReset }) {
  const [scenarioType, setScenarioType] = useState('SPEED_SURGE');
  const [speedMultiplier, setSpeedMultiplier] = useState(2.5);

  const handleSimulate = () => {
    if (!sampleToken) return;
    onRunSimulation({
      sample_token: sampleToken,
      scenario_type: scenarioType,
      speed_multiplier: speedMultiplier,
      scenario_name: scenarioType === 'SPEED_SURGE' ? 'Target Speed Surge (2.5x)' : scenarioType === 'EMERGENCY_BRAKE_FAILURE' ? 'Sudden Brake Failure' : 'Aggressive Lane Drift Cut-In'
    });
  };

  return (
    <div className="glass-panel rounded-xl p-4 border border-slate-800 flex flex-col gap-3">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center gap-2 text-xs font-semibold text-amber-400">
          <Zap className="w-4 h-4" />
          <span>Counterfactual Incident Simulation</span>
        </div>
        {isSimulating && (
          <span className="text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/40 px-2 py-0.5 rounded font-mono animate-pulse flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> Counterfactual Mode Active
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
        {/* Scenario Selection */}
        <div>
          <label className="block text-slate-400 mb-1 font-medium">Simulation Scenario</label>
          <select
            value={scenarioType}
            onChange={(e) => setScenarioType(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-amber-500"
          >
            <option value="SPEED_SURGE">⚡ Target Speed Surge (Collision Risk)</option>
            <option value="EMERGENCY_BRAKE_FAILURE">🛑 Emergency Brake Failure (Rear-End Hazard)</option>
            <option value="LANE_DRIFT_CUT_IN">🔀 Aggressive Lane Drift / Cut-In</option>
          </select>
        </div>

        {/* Speed Multiplier Slider */}
        <div>
          <div className="flex justify-between text-slate-400 mb-1 font-medium">
            <span>Speed Factor</span>
            <span className="text-amber-400 font-mono">{speedMultiplier}x</span>
          </div>
          <input
            type="range"
            min="1.2"
            max="4.0"
            step="0.1"
            value={speedMultiplier}
            onChange={(e) => setSpeedMultiplier(parseFloat(e.target.value))}
            className="w-full accent-amber-500 cursor-pointer"
          />
        </div>
      </div>

      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={handleSimulate}
          disabled={!sampleToken}
          className="flex-1 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-slate-950 font-semibold py-2 px-3 rounded-lg text-xs flex items-center justify-center gap-2 transition-all shadow-lg shadow-amber-600/20 active:scale-95"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>Run Counterfactual Simulation</span>
        </button>

        {isSimulating && (
          <button
            onClick={onReset}
            className="bg-slate-800 hover:bg-slate-700 text-slate-300 py-2 px-3 rounded-lg text-xs flex items-center gap-1.5 transition-all border border-slate-700"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reset Ground Truth</span>
          </button>
        )}
      </div>
    </div>
  );
}
