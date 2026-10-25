import React from 'react';
import { Sliders, Download, Database } from 'lucide-react';

export default function FeedbackExport() {
  const handleExport = (format) => {
    window.open(`/api/moderator/feedback/export?format=${format}`, '_blank');
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-6 rounded-2xl">
        <h1 className="text-xl font-bold text-slate-900 dark:text-white">Moderator Corrections & Adaptive Learning Export</h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Export the logged dataset comparing initial AI suggestions against human moderator overrides. This data powers adaptive research feedback loops without unsafe automatic model retraining.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-6 rounded-2xl space-y-4 text-center">
          <div className="inline-flex p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-2xl">
            <Download className="w-8 h-8 text-emerald-400" />
          </div>
          <h2 className="text-sm font-bold text-slate-900 dark:text-white">Export Dataset (CSV)</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Suitable for Excel, Python pandas, R analysis, or statistical evaluation.</p>
          <button
            onClick={() => handleExport('csv')}
            className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl text-xs shadow-lg shadow-emerald-600/30"
          >
            Download Corrections CSV
          </button>
        </div>

        <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-6 rounded-2xl space-y-4 text-center">
          <div className="inline-flex p-3 bg-indigo-500/10 border border-indigo-500/30 rounded-2xl">
            <Database className="w-8 h-8 text-indigo-400" />
          </div>
          <h2 className="text-sm font-bold text-slate-900 dark:text-white">Export Dataset (JSON)</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">Suitable for ML fine-tuning pipelines, evaluation scripts, or JSON schema tools.</p>
          <button
            onClick={() => handleExport('json')}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl text-xs shadow-lg shadow-indigo-600/30"
          >
            Download Corrections JSON
          </button>
        </div>
      </div>
    </div>
  );
}
