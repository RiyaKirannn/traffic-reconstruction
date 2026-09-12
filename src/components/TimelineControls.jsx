import React from 'react';
import { Play, Pause, SkipBack, SkipForward, Film, Database } from 'lucide-react';

export default function TimelineControls({ scenes, currentSceneToken, onSelectScene, samples, currentSampleIndex, onSelectSampleIndex, isPlaying, onTogglePlay }) {
  return (
    <div className="glass-panel rounded-xl px-4 py-2.5 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
      {/* Scene Dropdown Selector */}
      <div className="flex items-center gap-2.5 w-full md:w-auto">
        <Database className="w-4 h-4 text-blue-400 shrink-0" />
        <span className="text-xs font-semibold text-slate-300 whitespace-nowrap">nuScenes Scene:</span>
        <select
          value={currentSceneToken}
          onChange={(e) => onSelectScene(e.target.value)}
          className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500 w-full md:w-64"
        >
          {scenes.map((s) => (
            <option key={s.token} value={s.token}>
              {s.name} ({s.description.slice(0, 30)}...)
            </option>
          ))}
        </select>
      </div>

      {/* Playback Controls */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => onSelectSampleIndex(Math.max(0, currentSampleIndex - 1))}
          className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-all border border-slate-700"
          title="Previous Keyframe"
        >
          <SkipBack className="w-4 h-4" />
        </button>

        <button
          onClick={onTogglePlay}
          className="p-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-all shadow-md shadow-blue-600/20 active:scale-95"
          title={isPlaying ? "Pause Scene" : "Play Scene"}
        >
          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 fill-current" />}
        </button>

        <button
          onClick={() => onSelectSampleIndex(Math.min(samples.length - 1, currentSampleIndex + 1))}
          className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-all border border-slate-700"
          title="Next Keyframe"
        >
          <SkipForward className="w-4 h-4" />
        </button>
      </div>

      {/* Timeline Slider */}
      <div className="flex items-center gap-3 w-full md:w-80">
        <Film className="w-4 h-4 text-slate-400 shrink-0" />
        <input
          type="range"
          min="0"
          max={Math.max(0, samples.length - 1)}
          value={currentSampleIndex}
          onChange={(e) => onSelectSampleIndex(parseInt(e.target.value))}
          className="w-full accent-blue-500 cursor-pointer"
        />
        <span className="text-xs font-mono text-slate-400 whitespace-nowrap">
          {samples.length > 0 ? `${currentSampleIndex + 1}/${samples.length}` : '0/0'}
        </span>
      </div>
    </div>
  );
}
