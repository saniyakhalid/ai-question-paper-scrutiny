import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import Badge from '../components/common/Badge';
import ConfirmModal from '../components/common/ConfirmModal';
import { downloadScrutinyReport } from '../utils/exportUtils';
import {
  Clock, PlayCircle, Loader2, Filter, Trash2, MessageSquare,
  FileText, Download, CheckCircle2, AlertTriangle, X, ShieldCheck
} from 'lucide-react';

const STUCK = new Set(['SUBMITTED', 'EXTRACTED', 'ANALYZING', 'EXTRACTION_FAILED', 'FAILED', 'PARSED']);

export default function PaperHistory() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [historyList, setHistoryList] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [selectedSubject, setSelectedSubject] = useState('');
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [resumingId, setResumingId] = useState(null);
  const [actionError, setActionError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  // Delete Modal State
  const [paperToDelete, setPaperToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  // Moderator Feedback Modal State
  const [feedbackModalPaper, setFeedbackModalPaper] = useState(null);

  // Quick download state
  const [downloadingId, setDownloadingId] = useState(null);

  useEffect(() => {
    api.get('/subjects')
      .then((res) => setSubjects(res.data || []))
      .catch((err) => console.error('Failed to load subjects', err));
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [selectedSubject]);

  const fetchHistory = () => {
    setLoading(true);
    const params = selectedSubject ? { subject_id: selectedSubject } : {};
    api.get('/history', { params })
      .then((res) => setHistoryList(res.data || []))
      .catch((err) => console.error('Failed to fetch history:', err))
      .finally(() => setLoading(false));
  };

  const inspectTimeline = (paperId) => {
    api.get(`/history/${paperId}`)
      .then((res) => setTimeline(res.data))
      .catch((err) => console.error(err));
  };

  const resumeScrutiny = async (paperId) => {
    setActionError('');
    setActionSuccess('');
    setResumingId(paperId);
    try {
      await api.post(`/papers/${paperId}/resume`, null, { timeout: 180000 });
      setActionSuccess('Scrutiny analysis resumed successfully.');
      fetchHistory();
      navigate(`/papers/${paperId}`);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setActionError(typeof detail === 'string' ? detail : 'Failed to resume scrutiny.');
    } finally {
      setResumingId(null);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!paperToDelete) return;
    setDeleting(true);
    setActionError('');
    setActionSuccess('');
    try {
      const res = await api.delete(`/history/${paperToDelete.paper_id}`);
      setActionSuccess(res.data?.message || 'Paper and associated scrutiny records deleted successfully.');
      setPaperToDelete(null);
      if (timeline?.paper_info?.id === paperToDelete.paper_id) {
        setTimeline(null);
      }
      fetchHistory();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setActionError(typeof detail === 'string' ? detail : 'Failed to delete paper history.');
      setPaperToDelete(null);
    } finally {
      setDeleting(false);
    }
  };

  const handleQuickDownload = async (paper) => {
    try {
      setDownloadingId(paper.paper_id);
      await downloadScrutinyReport(paper.paper_id, 'pdf', `${paper.subject_code}_Paper_${paper.paper_id}`);
    } catch (err) {
      setActionError('Failed to download PDF report.');
    } finally {
      setDownloadingId(null);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-500">
        Loading Permanent Scrutiny History...
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Banner */}
      <div className="bg-white border border-slate-200 p-6 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900">
            Permanent Scrutiny History & Audit Log
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Complete institutional archive of question papers, AI scrutiny metrics, moderator feedback, and audit timeline.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={selectedSubject}
            onChange={(e) => setSelectedSubject(e.target.value)}
            className="bg-slate-50 border border-slate-200 text-slate-700 text-xs rounded-xl px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="">All Subjects</option>
            {subjects.map((s) => (
              <option key={s.id} value={s.id}>
                [{s.code}] {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {actionSuccess && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-700 dark:text-emerald-400 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess('')} className="text-emerald-500 hover:text-emerald-700">✕</button>
        </div>
      )}

      {actionError && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-700 dark:text-rose-400 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{actionError}</span>
          </div>
          <button onClick={() => setActionError('')} className="text-rose-500 hover:text-rose-700">✕</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Logs Table */}
        <div className="lg:col-span-2 bg-white border border-slate-200 p-5 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
              <span>Question Paper Examination Logs</span>
              <span className="text-xs text-adcet-navy font-mono font-bold">
                ({historyList.length})
              </span>
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
                <tr>
                  <th className="p-3">Paper Details</th>
                  <th className="p-3">Uploaded By</th>
                  <th className="p-3">Score</th>
                  <th className="p-3">Decision / Status</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-slate-700">
                {historyList.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-slate-400 italic">
                      No question paper scrutiny records found.
                    </td>
                  </tr>
                ) : (
                  historyList.map((h) => {
                    const stuck = STUCK.has(h.status) && !h.overall_score;
                    const isAnalyzing = h.status === 'ANALYZING';
                    const isFailed = h.status === 'FAILED' || h.status === 'EXTRACTION_FAILED';
                    const hasRemarks = !!h.moderator_remarks;
                    const canDelete = user?.role === 'ADMIN' || user?.role === 'MODERATOR' || (user?.role === 'FACULTY' && h.status !== 'APPROVED');

                    return (
                      <tr key={h.paper_id} className="hover:bg-slate-50 transition-colors">
                        <td className="p-3">
                          <p className="font-bold text-slate-900">{h.title}</p>
                          <p className="text-[11px] text-slate-500">
                            {h.subject_code} - {h.subject_name} • {h.exam_type}
                          </p>
                        </td>

                        <td className="p-3 text-slate-600 dark:text-slate-300">
                          {h.uploaded_by}
                        </td>

                        <td className="p-3 font-bold">
                          {isAnalyzing ? (
                            <span className="text-amber-500 font-semibold animate-pulse">ANALYZING...</span>
                          ) : isFailed ? (
                            <span className="text-rose-600 dark:text-rose-400 font-semibold">FAILED</span>
                          ) : (h.overall_score !== null && h.overall_score !== undefined && !isNaN(h.overall_score)) ? (
                            <span className="text-adcet-navy font-bold">
                              {Number(h.overall_score).toFixed(1)}/100
                            </span>
                          ) : (
                            <span className="text-slate-400 font-normal">N/A</span>
                          )}
                        </td>

                        <td className="p-3">
                          <div className="flex flex-col items-start gap-1">
                            <Badge status={h.moderator_decision || h.status} />
                            {hasRemarks && (
                              <button
                                type="button"
                                onClick={() => setFeedbackModalPaper(h)}
                                className="inline-flex items-center text-[10px] font-semibold text-adcet-navy hover:underline mt-0.5"
                              >
                                <MessageSquare className="w-3 h-3 mr-1" />
                                <span>View Moderator Feedback</span>
                              </button>
                            )}
                          </div>
                        </td>

                        <td className="p-3 text-right whitespace-nowrap space-x-1.5">
                          {stuck && (
                            <button
                              type="button"
                              onClick={() => resumeScrutiny(h.paper_id)}
                              disabled={resumingId === h.paper_id}
                              className="inline-flex items-center px-2 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-[11px] font-semibold disabled:opacity-50"
                              title="Resume scrutiny pipeline"
                            >
                              {resumingId === h.paper_id ? (
                                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                              ) : (
                                <PlayCircle className="w-3 h-3 mr-1" />
                              )}
                              Run Scrutiny
                            </button>
                          )}

                          <button
                            type="button"
                            onClick={() => inspectTimeline(h.paper_id)}
                            className="px-2 py-1 bg-brand-600/15 hover:bg-brand-600 text-brand-700 dark:text-indigo-300 hover:text-white rounded-lg border border-brand-500/30 text-[11px] font-semibold transition-colors"
                            title="Inspect audit trail"
                          >
                            Audit
                          </button>

                          <button
                            type="button"
                            onClick={() => navigate(`/papers/${h.paper_id}`)}
                            className="px-2 py-1 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-900 rounded-lg text-[11px] font-semibold transition-colors"
                          >
                            Scrutiny
                          </button>

                          {h.overall_score && (
                            <button
                              type="button"
                              onClick={() => handleQuickDownload(h)}
                              disabled={downloadingId === h.paper_id}
                              className="p-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-brand-50 text-slate-600 hover:text-brand-600 rounded-lg text-[11px] transition-colors inline-flex items-center"
                              title="Download PDF Scrutiny Report"
                            >
                              {downloadingId === h.paper_id ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              ) : (
                                <Download className="w-3.5 h-3.5" />
                              )}
                            </button>
                          )}

                          {canDelete && (
                            <button
                              type="button"
                              onClick={() => setPaperToDelete(h)}
                              className="p-1.5 text-rose-500 hover:bg-rose-500/10 rounded-lg transition-colors inline-flex items-center"
                              title="Delete question paper and scrutiny records"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Step-by-Step Audit Timeline */}
        <div className="bg-white border border-slate-200 p-5 rounded-2xl space-y-4">
          <h2 className="text-sm font-bold text-slate-900 flex items-center">
            <Clock className="w-4 h-4 mr-2 text-adcet-navy" />
            <span>Audit Timeline & Events</span>
          </h2>

          {!timeline ? (
            <p className="text-xs text-slate-500 italic">
              Click &quot;Audit&quot; on any paper to inspect its complete immutable audit log and status progression.
            </p>
          ) : (
            <div className="space-y-4">
              <div className="p-3 bg-slate-50/80 rounded-xl border border-slate-200 text-xs space-y-1">
                <p className="font-bold text-adcet-navy">{timeline.paper_info?.title}</p>
                <p className="text-slate-500">
                  {timeline.paper_info?.subject_code} - {timeline.paper_info?.subject_name}
                </p>
                <p className="text-[11px] text-slate-500">
                  Uploaded by: {timeline.paper_info?.uploaded_by} • Status: {timeline.paper_info?.status}
                </p>
              </div>

              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wide text-slate-600">Moderator decision history</h3>
                {timeline.moderator_reviews?.length ? timeline.moderator_reviews.map((review) => (
                  <div key={review.id} className="rounded-xl border border-slate-200 bg-white p-3 text-xs space-y-1.5">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-semibold text-slate-900">{review.moderator || 'Moderator'}</span>
                      <span className="text-[10px] text-slate-500">{review.created_at ? new Date(review.created_at).toLocaleString() : 'Time not recorded'}</span>
                    </div>
                    <p className="text-slate-700">
                      {review.previous_status || 'Prior status unavailable'} <span aria-hidden="true">→</span> {review.new_status || review.decision}
                    </p>
                    {review.remarks && <p className="leading-relaxed text-slate-600">{review.remarks}</p>}
                  </div>
                )) : (
                  <p className="rounded-xl border border-dashed border-slate-300 p-3 text-xs text-slate-500">No moderator decisions have been recorded for this paper.</p>
                )}
              </div>

              <div className="space-y-3 relative pl-4 border-l border-slate-200">
                {timeline.audit_timeline?.length ? (
                  timeline.audit_timeline.map((ev) => (
                    <div key={ev.id} className="relative space-y-1">
                      <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-brand-600 border border-white dark:border-slate-900" />
                      <p className="text-[10px] font-mono text-slate-500">
                        {ev.timestamp ? new Date(ev.timestamp).toLocaleString() : ''}
                      </p>
                      <p className="text-xs font-bold text-slate-900">{ev.action}</p>
                      <p className="text-xs text-slate-600">{ev.details}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-500">No audit timeline events recorded for this paper.</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={paperToDelete !== null}
        title="Delete Question Paper & Scrutiny Records"
        message={`Are you sure you want to delete "${paperToDelete?.title}" (${paperToDelete?.subject_code})? This permanently deletes all extracted questions, scrutiny reports, rule results, findings, and physical document files from the database.`}
        confirmLabel="Delete Permanently"
        confirmVariant="danger"
        loading={deleting}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setPaperToDelete(null)}
      />

      {/* Moderator Feedback Inspection Modal */}
      {feedbackModalPaper && (
        <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 max-w-lg w-full shadow-2xl space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-brand-600/10 text-adcet-navy rounded-xl">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    Official Moderator Feedback & Remarks
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    {feedbackModalPaper.title} • {feedbackModalPaper.subject_code}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setFeedbackModalPaper(null)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-slate-500">Binding Decision:</span>
                <Badge status={feedbackModalPaper.moderator_decision || feedbackModalPaper.status} />
              </div>

              {feedbackModalPaper.moderator_name && (
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                  <span className="text-slate-500">Reviewed By:</span>
                  <p className="font-bold text-slate-900 mt-0.5">{feedbackModalPaper.moderator_name}</p>
                </div>
              )}

              <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl space-y-1">
                <span className="font-bold text-amber-700 dark:text-amber-400">Moderator Remarks:</span>
                <p className="text-slate-800 dark:text-slate-200 leading-relaxed">
                  {feedbackModalPaper.moderator_remarks || 'No written remarks entered.'}
                </p>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setFeedbackModalPaper(null)}
                className="px-4 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 text-slate-800 dark:text-slate-200 rounded-xl text-xs font-semibold transition-colors"
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
