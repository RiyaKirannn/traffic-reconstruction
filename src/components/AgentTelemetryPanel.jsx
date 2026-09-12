import React from 'react';
import { Cpu, CheckCircle2, AlertCircle, Clock } from 'lucide-react';

export default function AgentTelemetryPanel({ telemetry = [] }) {
  const totalTime = telemetry.reduce((acc, curr) => acc + (curr.execution_time_ms || 0), 0);

  return (
    <div className="glass-panel rounded-xl p-4 flex flex-col h-full border border-slate-800">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
          <Cpu className="w-4 h-4 text-purple-400" />
          <span>Multi-Agent Execution Pipeline</span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] font-mono text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
          <Clock className="w-3 h-3" /> {totalTime.toFixed(1)} ms
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {telemetry.length === 0 ? (
          <div className="text-slate-500 text-xs py-4 text-center">No agent pipeline execution recorded</div>
        ) : (
          telemetry.map((agent, idx) => (
            <div key={idx} className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80 hover:border-purple-500/30 transition-all text-xs">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5 font-medium text-slate-200">
                  {agent.status === 'SUCCESS' ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                  )}
                  <span>{agent.agent_name}</span>
                </div>
                <span className="font-mono text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
                  {agent.execution_time_ms} ms
                </span>
              </div>
              <p className="text-[11px] text-slate-400 line-clamp-2">{agent.summary}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
