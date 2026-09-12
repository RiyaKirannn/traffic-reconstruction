import React from 'react';
import { Camera, Eye, Layers } from 'lucide-react';

export default function CameraView({ sampleToken, worldModel }) {
  const imageUrl = sampleToken ? `/api/camera-image/${sampleToken}` : null;
  const objectCount = worldModel ? Object.keys(worldModel.objects || {}).length : 0;
  const criticalCount = worldModel ? (worldModel.interactions || []).filter(i => i.risk_level === 'CRITICAL' || i.risk_level === 'HIGH').length : 0;

  return (
    <div className="glass-panel rounded-xl overflow-hidden flex flex-col h-full border border-slate-800">
      {/* Header */}
      <div className="px-4 py-2.5 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
          <Camera className="w-4 h-4 text-blue-400" />
          <span>Synchronized Front Camera (CAM_FRONT)</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
          <span className="flex items-center gap-1 bg-slate-800 px-2 py-0.5 rounded text-blue-400">
            <Layers className="w-3 h-3" /> {objectCount} Boxes HUD
          </span>
          {criticalCount > 0 && (
            <span className="bg-red-500/20 text-red-400 border border-red-500/40 px-2 py-0.5 rounded animate-pulse">
              ⚠️ {criticalCount} Risk Alerts
            </span>
          )}
        </div>
      </div>

      {/* Image Container */}
      <div className="relative flex-1 bg-slate-950 flex items-center justify-center overflow-hidden">
        {imageUrl ? (
          <div className="relative w-full h-full flex items-center justify-center">
            <img
              src={imageUrl}
              alt="Front Camera Feed"
              className="max-w-full max-h-full object-contain"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
            {/* Camera Overlay HUD Grid */}
            <div className="absolute inset-0 pointer-events-none border border-blue-500/10 grid grid-cols-3 grid-rows-3">
              <div className="border-r border-b border-blue-500/10"></div>
              <div className="border-r border-b border-blue-500/10"></div>
              <div className="border-b border-blue-500/10"></div>
              <div className="border-r border-b border-blue-500/10"></div>
              <div className="border-r border-b border-blue-500/10 flex items-center justify-center">
                <div className="w-6 h-6 border border-blue-400/40 rounded-full flex items-center justify-center">
                  <div className="w-1 h-1 bg-blue-400 rounded-full"></div>
                </div>
              </div>
              <div className="border-b border-blue-500/10"></div>
            </div>
            
            {/* Live Camera Stamp */}
            <div className="absolute top-2 left-2 bg-slate-900/90 text-slate-300 text-[10px] font-mono px-2 py-1 rounded border border-slate-700/50">
              FPS: 30 | RES: 1600x900 | NuScenes Keyframe
            </div>
          </div>
        ) : (
          <div className="text-slate-500 text-xs flex flex-col items-center gap-2">
            <Eye className="w-8 h-8 text-slate-600 animate-bounce" />
            <span>Select a scene sample to stream front camera feed</span>
          </div>
        )}
      </div>
    </div>
  );
}
