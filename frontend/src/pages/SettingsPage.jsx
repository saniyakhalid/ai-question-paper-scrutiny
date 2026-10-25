import React from 'react';
import { Settings, ShieldCheck, Key, Cpu } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">System Configuration & AI Provider</h1>
        <p className="text-sm text-slate-500">AI provider settings are read by the backend from its environment.</p>
      </div>

      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
          <Cpu className="w-4 h-4 text-blue-600" /> Active AI Provider Configuration
        </h3>

        <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-2">
          <div className="flex justify-between">
            <span className="font-semibold text-slate-600">AI Provider:</span>
            <span className="font-bold text-blue-700">Set with AI_PROVIDER</span>
          </div>
          <div className="flex justify-between">
            <span className="font-semibold text-slate-600">Configured Model:</span>
            <span className="font-mono text-slate-800">GEMINI_MODEL environment variable</span>
          </div>
          <div className="flex justify-between">
            <span className="font-semibold text-slate-600">Environment File:</span>
            <span className="font-mono text-slate-800">backend/.env</span>
          </div>
        </div>

        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded-lg text-xs space-y-1">
          <div className="font-bold flex items-center gap-1">
            <ShieldCheck className="w-4 h-4 text-emerald-600" /> Key Security Guarantee
          </div>
          <p className="text-slate-700">
            The frontend does not configure or display provider credentials. Set AI_PROVIDER=gemini and GEMINI_API_KEY in the backend environment to enable Gemini; otherwise reports identify offline heuristic mode.
          </p>
        </div>
      </div>
    </div>
  );
}
