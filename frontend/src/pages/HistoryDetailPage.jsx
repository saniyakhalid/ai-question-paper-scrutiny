import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { historyAPI } from '../services/api';
import { Clock, ShieldCheck, UserCheck, Edit3, Award } from 'lucide-react';

export default function HistoryDetailPage() {
  const { id } = useParams();
  const [historyData, setHistoryData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadDetail = async () => {
      try {
        const res = await historyAPI.getDetail(id);
        setHistoryData(res.data);
      } catch (err) {
        console.error("Failed to load history detail", err);
      } finally {
        setLoading(false);
      }
    };
    loadDetail();
  }, [id]);

  if (loading) return <div className="p-8 text-center text-slate-500">Loading audit history timeline...</div>;
  if (!historyData) return <div className="p-8 text-center text-red-500">History record not found.</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
        <h1 className="text-xl font-bold text-slate-900">Audit History Timeline: {historyData.title}</h1>
        <p className="text-xs text-slate-500">Paper ID: #{historyData.paper_id} | Status: <span className="font-bold text-blue-600">{historyData.status}</span></p>

        {/* Audit Timeline */}
        <div className="mt-6 space-y-4 relative before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
          {historyData.audit_timeline.map((log, idx) => (
            <div key={log.id} className="flex items-start space-x-4 relative">
              <div className="w-7 h-7 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold shrink-0 z-10">
                {idx + 1}
              </div>
              <div className="flex-1 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900 uppercase tracking-wider">{log.action}</span>
                  <span className="text-slate-400 font-mono">{new Date(log.timestamp).toLocaleString()}</span>
                </div>
                <div className="text-slate-600">
                  <span className="font-semibold text-slate-700">Entity:</span> {log.entity} #{log.entity_id} | <span className="font-semibold text-slate-700">Role:</span> {log.user_role}
                </div>
                {log.metadata_json && (
                  <pre className="p-2 bg-slate-100 rounded-md font-mono text-2xs text-slate-800 overflow-x-auto mt-1">
                    {JSON.stringify(log.metadata_json, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
