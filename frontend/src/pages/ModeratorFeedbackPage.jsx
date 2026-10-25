import React, { useState, useEffect } from 'react';
import { moderatorAPI } from '../services/api';
import { Award, Download, CheckCircle2 } from 'lucide-react';

export default function ModeratorFeedbackPage() {
  const [feedback, setFeedback] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadFeedback = async () => {
      try {
        const res = await moderatorAPI.exportFeedbackCSV();
        // Just checking endpoint availability
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadFeedback();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Moderator Feedback & AI Correction Dataset</h1>
          <p className="text-sm text-slate-500">Dataset of human moderator corrections over AI outputs for adaptive learning & evaluation</p>
        </div>

        <a
          href={moderatorAPI.exportFeedbackCSV()}
          download="moderator_feedback_dataset.csv"
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs rounded-lg shadow-xs flex items-center gap-2"
        >
          <Download className="w-4 h-4" /> Export Feedback Dataset (CSV)
        </a>
      </div>

      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <div className="p-4 bg-blue-50 border border-blue-200 text-blue-900 rounded-lg text-xs space-y-1">
          <div className="font-bold flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-blue-600" /> Research Contribution: Human-in-the-Loop Feedback Integration
          </div>
          <p className="text-slate-700">
            This module preserves all human moderator overrides (AI predicted value vs Moderator corrected value with justification reasons). The exported CSV dataset supports adaptive evaluation without unmonitored automated retraining.
          </p>
        </div>
      </div>
    </div>
  );
}
