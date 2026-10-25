import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { historyAPI } from '../services/api';
import { History, Search, FileText, ChevronRight } from 'lucide-react';

export default function HistoryListPage() {
  const [historyItems, setHistoryItems] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadHistory = async () => {
      try {
        const res = await historyAPI.list();
        setHistoryItems(res.data);
      } catch (err) {
        console.error("Failed to load history", err);
      } finally {
        setLoading(false);
      }
    };
    loadHistory();
  }, []);

  const filtered = historyItems.filter((h) =>
    h.title.toLowerCase().includes(search.toLowerCase()) ||
    h.subject?.code.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Permanent Scrutiny History Record</h1>
          <p className="text-sm text-slate-500">Immutable audit repository of all question paper uploads, AI outputs, and moderator decisions</p>
        </div>
      </div>

      <div className="relative">
        <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
        <input
          type="text"
          placeholder="Filter history by subject code, title, or academic year..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-lg text-sm"
        />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-500">Loading history records...</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-500">No matching history records.</div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
              <tr>
                <th className="py-3 px-4">Paper ID</th>
                <th className="py-3 px-4">Paper Title</th>
                <th className="py-3 px-4">Subject</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Uploaded Date</th>
                <th className="py-3 px-4 text-right">Audit Timeline</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50">
                  <td className="py-3 px-4 font-mono text-xs font-bold text-slate-600">#PAPER-{item.id}</td>
                  <td className="py-3 px-4 font-semibold text-slate-900">{item.title}</td>
                  <td className="py-3 px-4 text-slate-600">{item.subject?.code}</td>
                  <td className="py-3 px-4">
                    <span className="px-2.5 py-0.5 bg-slate-100 text-slate-800 font-bold text-xs rounded-full">
                      {item.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-500 text-xs">{new Date(item.created_at).toLocaleDateString()}</td>
                  <td className="py-3 px-4 text-right">
                    <Link
                      to={`/history/${item.id}`}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-800"
                    >
                      View Timeline <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
