import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import Badge from '../components/common/Badge';
import {
  FileText, Plus, ExternalLink, CheckCircle, Clock, AlertTriangle,
  XCircle, AlertCircle, MessageSquare, ShieldCheck, X
} from 'lucide-react';

export default function PapersListPage() {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [feedbackModalPaper, setFeedbackModalPaper] = useState(null);

  useEffect(() => {
    const loadPapers = async () => {
      try {
        const res = await api.get('/papers');
        setPapers(res.data || []);
      } catch (err) {
        setError(err.response?.data?.detail || 'Could not load question papers. Please try again.');
      } finally {
        setLoading(false);
      }
    };
    loadPapers();
  }, []);

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Submitted Question Papers</h1>
          <p className="text-sm text-slate-500">
            View paper scrutiny status, automated DSS scores, and chief moderator feedback
          </p>
        </div>

        <Link
          to="/papers/upload"
          className="w-fit px-4 py-2 bg-adcet-red hover:bg-red-700 text-white font-semibold text-sm rounded-lg shadow-sm flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> Upload New Paper
        </Link>
      </div>

      {error && (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-slate-500">Loading papers...</div>
        ) : error ? null : papers.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <p className="font-medium text-slate-700">No question papers submitted yet</p>
            <p className="text-xs text-slate-400 mt-1">Upload a paper to run AI analysis &amp; rule engine</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[960px] text-left border-collapse text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold text-xs uppercase tracking-wide">
                  <th className="py-3 px-4">Paper Title</th>
                  <th className="py-3 px-4">Subject</th>
                  <th className="py-3 px-4">Exam Type</th>
                  <th className="py-3 px-4">DSS Score</th>
                  <th className="py-3 px-4">Moderator Decision &amp; Feedback</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {papers.map((p) => {
                  const decisionStatus = p.moderator_decision || p.status;
                  const hasFeedback = !!p.moderator_feedback;
                  const isChangeRequested = decisionStatus === 'MODIFICATION_REQUIRED';

                  return (
                    <tr key={p.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-3.5 px-4">
                        <p className="font-bold text-slate-900">{p.title}</p>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          Paper #{p.id} • Academic Year {p.academic_year || '—'}
                        </p>
                      </td>
                      <td className="py-3.5 px-4 text-slate-600">
                        <span className="font-semibold text-slate-800">{p.subject?.code}</span>
                        {p.subject?.name && <span className="block text-[11px] text-slate-500">{p.subject.name}</span>}
                      </td>
                      <td className="py-3.5 px-4 text-slate-600">
                        {p.exam_type || 'Examination'}
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-800">
                        {p.overall_score != null ? `${Number(p.overall_score).toFixed(1)}%` : <span className="text-slate-400 font-normal">N/A</span>}
                      </td>
                      <td className="py-3.5 px-4 max-w-xs">
                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <Badge status={decisionStatus} />
                            {p.moderator_name && (
                              <span className="text-[10px] text-slate-400">by {p.moderator_name}</span>
                            )}
                          </div>

                          {hasFeedback ? (
                            <div className="mt-1">
                              <p className="text-[11px] text-slate-700 italic line-clamp-2 bg-slate-50 p-1.5 rounded border border-slate-200/60">
                                &ldquo;{p.moderator_feedback}&rdquo;
                              </p>
                              <button
                                type="button"
                                onClick={() => setFeedbackModalPaper(p)}
                                className="inline-flex items-center gap-1 text-[11px] font-semibold text-adcet-navy hover:underline mt-1 cursor-pointer"
                              >
                                <MessageSquare className="w-3 h-3 text-adcet-navy" />
                                <span>Read Full Feedback</span>
                              </button>
                            </div>
                          ) : (
                            <p className="text-[11px] text-slate-400 italic">Awaiting moderator feedback</p>
                          )}

                          {isChangeRequested && (
                            <div className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                              <AlertTriangle className="w-3 h-3 text-amber-600" />
                              <span>Action needed: revisions requested</span>
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-right space-x-2 whitespace-nowrap">
                        <Link
                          to={`/papers/${p.id}`}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-adcet-navy hover:bg-slate-800 text-white font-semibold text-xs transition-colors shadow-xs"
                        >
                          <span>Inspect Scrutiny</span>
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Moderator Feedback Inspection Modal */}
      {feedbackModalPaper && (
        <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-xs z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 max-w-lg w-full shadow-2xl space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-brand-600/10 text-adcet-navy rounded-xl">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Chief Moderator Scrutiny Feedback
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    {feedbackModalPaper.title} • {feedbackModalPaper.subject?.code || ''}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setFeedbackModalPaper(null)}
                className="text-slate-400 hover:text-slate-600 p-1 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-slate-500 font-medium">Official Decision:</span>
                <Badge status={feedbackModalPaper.moderator_decision || feedbackModalPaper.status} />
              </div>

              {feedbackModalPaper.moderator_name && (
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-slate-500 font-medium">Reviewed By:</span>
                  <p className="font-bold text-slate-900 mt-0.5">{feedbackModalPaper.moderator_name}</p>
                  {feedbackModalPaper.moderated_at && (
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      {new Date(feedbackModalPaper.moderated_at).toLocaleString()}
                    </p>
                  )}
                </div>
              )}

              <div className="p-3.5 bg-amber-500/10 border border-amber-500/30 rounded-xl space-y-1.5">
                <span className="font-bold text-amber-800 dark:text-amber-400 flex items-center space-x-1.5">
                  <MessageSquare className="w-4 h-4" />
                  <span>Moderator Feedback Message:</span>
                </span>
                <p className="text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap font-medium">
                  {feedbackModalPaper.moderator_feedback || 'No written remarks entered.'}
                </p>
              </div>

              {feedbackModalPaper.moderator_required_action && (
                <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-xl text-indigo-900 space-y-0.5">
                  <span className="font-bold">Required Action for Faculty:</span>
                  <p className="text-slate-800 leading-relaxed">
                    {feedbackModalPaper.moderator_required_action}
                  </p>
                </div>
              )}

              {(feedbackModalPaper.moderator_decision || feedbackModalPaper.status) === 'MODIFICATION_REQUIRED' && (
                <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-amber-800 flex items-start space-x-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-600" />
                  <div className="text-[11px] leading-relaxed">
                    <span className="font-semibold">Next step:</span> Please review the comments above and revise the question paper. You can then submit a revised version from the Upload page.
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-between items-center pt-2">
              <Link
                to={`/papers/${feedbackModalPaper.id}`}
                onClick={() => setFeedbackModalPaper(null)}
                className="text-xs font-semibold text-adcet-navy hover:underline inline-flex items-center gap-1"
              >
                <span>Go to Scrutiny Report</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </Link>
              <button
                type="button"
                onClick={() => setFeedbackModalPaper(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-semibold transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
