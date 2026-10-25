import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import Badge from '../components/common/Badge';
import ConfirmModal from '../components/common/ConfirmModal';
import { downloadScrutinyReport } from '../utils/exportUtils';
import {
  FileText, Download, CheckCircle2, AlertTriangle, XCircle, BookOpen,
  Brain, Sliders, ShieldCheck, ArrowLeft, ChevronDown, ChevronRight, Bug,
  PlayCircle, Loader2, MessageSquare, Clock, User, Sparkles, Check, AlertCircle
} from 'lucide-react';

function formatMarks(marks) {
  if (marks === null || marks === undefined || marks === '') return '—';
  return `${marks}`;
}

function confidenceLabel(score) {
  if (score == null) return { text: 'Unknown', cls: 'bg-slate-500/10 text-slate-500 border-slate-500/30' };
  if (score >= 0.85) return { text: 'High confidence', cls: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30' };
  if (score >= 0.75) return { text: 'Medium confidence', cls: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30' };
  return { text: 'Low confidence', cls: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30' };
}

function statusBadge(status) {
  const s = (status || 'PASS').toUpperCase();
  if (s === 'PASS') return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30';
  if (s === 'WARNING') return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30';
  return 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/30';
}

function roundVal(v) {
  return typeof v === 'number' ? v.toFixed(1) : v;
}

export default function PaperScrutiny() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [paper, setPaper] = useState(null);
  const [report, setReport] = useState(null);
  const [moderatorReview, setModeratorReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [runningScrutiny, setRunningScrutiny] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  // Moderator review submission state
  const [decision, setDecision] = useState('APPROVED');
  const [remarks, setRemarks] = useState('');
  const [requiredAction, setRequiredAction] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // UI state
  const [expandedGroups, setExpandedGroups] = useState({});
  const [showDebug, setShowDebug] = useState(false);
  const [pipelineError, setPipelineError] = useState('');
  const [downloadingFormat, setDownloadingFormat] = useState(null);
  const paperRequestId = useRef(0);

  const [editingUnitsOpen, setEditingUnitsOpen] = useState(false);
  const [subjectUnits, setSubjectUnits] = useState([]);
  const [tempUnits, setTempUnits] = useState([]);
  const [savingUnits, setSavingUnits] = useState(false);

  const isModeratorOrAdmin = user?.role === 'MODERATOR' || user?.role === 'ADMIN';
  const canEditUnits = isModeratorOrAdmin || (user && paper && paper.uploaded_by_id === user.id);

  const openEditUnits = async () => {
    if (!paper) return;
    try {
      const res = await api.get(`/subjects/${paper.subject_id}/syllabus`);
      const units = res.data || [];
      setSubjectUnits(units);
      setTempUnits(paper.selected_units_json || units.map((u) => u.unit_number));
      setEditingUnitsOpen(true);
    } catch (e) {
      alert('Could not load syllabus units for this subject');
    }
  };

  const handleSaveUnitsAndRescrutinize = async () => {
    if (tempUnits.length === 0) {
      alert('Please select at least one unit.');
      return;
    }
    setSavingUnits(true);
    try {
      await api.put(`/papers/${id}/units`, { selected_units: tempUnits });
      setEditingUnitsOpen(false);
      setRunningScrutiny(true);
      await api.post(`/papers/${id}/resume`, null, { timeout: 180000 });
      await fetchPaperData();
      setSuccessMsg(`Active units updated to ${tempUnits.join(', ')} and scrutiny re-analyzed.`);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to update units and re-scrutinize.');
    } finally {
      setSavingUnits(false);
      setRunningScrutiny(false);
    }
  };

  useEffect(() => {
    fetchPaperData();
    return () => { paperRequestId.current += 1; };
  }, [id]);

  const fetchPaperData = async () => {
    const requestId = ++paperRequestId.current;
    setLoading(true);
    setPipelineError('');
    setPaper(null);
    setReport(null);
    setModeratorReview(null);
    try {
      const pRes = await api.get(`/papers/${id}`);
      if (requestId !== paperRequestId.current) return;
      setPaper(pRes.data);

      try {
        const rRes = await api.get(`/scrutiny/${id}`);
        if (requestId === paperRequestId.current) setReport(rRes.data);
      } catch {
        if (requestId === paperRequestId.current) setReport(null);
      }

      try {
        const revRes = await api.get(`/moderator/reviews/${id}`);
        if (requestId !== paperRequestId.current) return;
        if (revRes.data?.has_review) {
          setModeratorReview(revRes.data.review);
          setRemarks(revRes.data.review.remarks || '');
          setRequiredAction(revRes.data.review.required_action || '');
          setDecision(revRes.data.review.decision || 'APPROVED');
        }
      } catch {
        if (requestId === paperRequestId.current) setModeratorReview(null);
      }
    } catch (err) {
      if (requestId === paperRequestId.current) {
        setPipelineError(err.response?.data?.detail || 'Could not load this question paper.');
      }
    } finally {
      if (requestId === paperRequestId.current) setLoading(false);
    }
  };

  const runScrutinyNow = async () => {
    setRunningScrutiny(true);
    setPipelineError('');
    try {
      await api.post(`/papers/${id}/resume`, null, { timeout: 180000 });
      await fetchPaperData();
      setSuccessMsg('Scrutiny analysis completed successfully.');
    } catch (err) {
      const detail = err.response?.data?.detail;
      setPipelineError(typeof detail === 'string' ? detail : 'Scrutiny failed. Check if the PDF is text-searchable.');
    } finally {
      setRunningScrutiny(false);
    }
  };

  const handleDownload = async (format) => {
    try {
      setDownloadingFormat(format);
      await downloadScrutinyReport(id, format, paper?.title);
    } catch (err) {
      alert(`Failed to download ${format.toUpperCase()} report. Please check that analysis is complete.`);
    } finally {
      setDownloadingFormat(null);
    }
  };

  const handleOpenConfirm = (e) => {
    e.preventDefault();
    if (!isModeratorOrAdmin || paper?.validation_status !== 'VALID_MATCH' || !report) return;
    if (!remarks.trim()) {
      setErrorMsg('Please enter detailed moderator feedback remarks and evaluation reasoning before submitting.');
      return;
    }
    setErrorMsg('');
    setConfirmModalOpen(true);
  };

  const handleSubmitDecisionConfirmed = async () => {
    setSubmitting(true);
    setSuccessMsg('');
    setErrorMsg('');

    try {
      const res = await api.post(`/moderator/reviews/${id}`, {
        decision,
        remarks: remarks.trim(),
        required_action: requiredAction.trim() || undefined,
        corrections: [],
      });
      const labelMap = {
        APPROVED: 'Approved',
        MODIFICATION_REQUIRED: 'Changes Requested / Modification Required',
        REVIEW_DECLINED: 'Review Declined',
        REJECTED: 'Rejected',
      };
      setSuccessMsg(`Decision confirmed and logged as "${labelMap[decision] || decision}". Scrutiny record updated.`);
      setModeratorReview(res.data);
      setConfirmModalOpen(false);
      await fetchPaperData();
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Failed to submit moderator review.');
      setConfirmModalOpen(false);
    } finally {
      setSubmitting(false);
    }
  };

  const activeReview = moderatorReview || (paper?.moderator_feedback || paper?.moderator_decision ? {
    decision: paper.moderator_decision || paper.status,
    remarks: paper.moderator_feedback || '',
    required_action: paper.moderator_required_action,
    moderator_name: paper.moderator_name || 'Chief Examination Moderator',
    created_at: paper.moderated_at,
  } : null);

  const questions = paper?.questions || [];
  const analyzableQuestions = useMemo(
    () => questions.filter((q) => (q.question_type || 'QUESTION').toUpperCase() !== 'QUESTION_GROUP'),
    [questions]
  );

  const findings = report?.findings || [];
  const findingFor = (questionId, type) =>
    findings.find((f) => f.question_id === questionId && f.finding_type === type);

  const groupedRows = useMemo(() => {
    const parents = questions.filter((q) => (q.question_type || '').toUpperCase() === 'QUESTION_GROUP');
    if (!parents.length) return questions;

    const childrenByParent = {};
    const unparented = [];
    questions.forEach((q) => {
      if ((q.question_type || '').toUpperCase() === 'QUESTION_GROUP') return;
      if (q.parent_question_id) {
        childrenByParent[q.parent_question_id] = childrenByParent[q.parent_question_id] || [];
        childrenByParent[q.parent_question_id].push(q);
      } else {
        unparented.push(q);
      }
    });

    const ordered = [];
    parents.forEach((p) => {
      ordered.push(p);
      const kids = childrenByParent[p.id] || [];
      if (expandedGroups[p.id] !== false) {
        ordered.push(...kids);
      }
    });
    ordered.push(...unparented);
    return ordered;
  }, [questions, expandedGroups]);

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-500">
        Loading Question Paper & Scrutiny Details...
      </div>
    );
  }

  if (!paper) {
    return (
      <div className="p-8 text-center text-rose-500">
        Question paper not found or access restricted.
      </div>
    );
  }

  const tabs = [
    { id: 'overview', label: 'Overview & Exports', icon: FileText },
    { id: 'breakdown', label: 'Question Breakdown', icon: BookOpen },
    { id: 'bloom', label: 'Bloom & CO Mapping', icon: Brain },
    { id: 'grammar', label: 'Grammar & Quality', icon: Sliders },
    { id: 'similarity', label: 'Similarity Flags', icon: AlertTriangle },
    { id: 'rules', label: 'Rule Validation', icon: CheckCircle2 },
    {
      id: 'decision',
      label: isModeratorOrAdmin ? 'Moderator Decision Room' : 'Moderator Feedback & Decision',
      icon: ShieldCheck,
      badge: moderatorReview ? 'Reviewed' : null,
    },
  ];

  const panel = 'bg-white border border-slate-200 p-6 rounded-2xl';
  const muted = 'text-slate-500';

  // Consistent scrutiny score
  const displayScore = paper.overall_score ?? report?.overall_score;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Info Banner */}
      <div className={`flex flex-col md:flex-row md:items-center justify-between gap-4 ${panel}`}>
        <div>
          <button
            onClick={() => navigate('/dashboard')}
            className={`text-xs ${muted} hover:text-slate-900 dark:hover:text-white flex items-center mb-2`}
          >
            <ArrowLeft className="w-3.5 h-3.5 mr-1" /> Back to Dashboard
          </button>
          <div className="flex items-center space-x-3 flex-wrap gap-y-2">
            <h1 className="text-xl font-display font-bold text-slate-900">{paper.title}</h1>
            <Badge status={paper.status} />
            {moderatorReview?.decision && (
              <Badge variant="warning" className="uppercase font-mono">
                Moderator: {moderatorReview.decision}
              </Badge>
            )}
          </div>
          <p className={`text-xs ${muted} mt-1`}>
            Subject: <strong className="text-slate-800 dark:text-slate-200">{paper.subject?.code} - {paper.subject?.name}</strong> | Academic Year: {paper.academic_year} | Exam: {paper.exam_type}
          </p>
          <p className={`text-[11px] mt-2 font-semibold ${paper.validation_status === 'VALID_MATCH' ? 'text-emerald-700' : 'text-rose-700'}`}>
            Document validation: {(paper.validation_status || 'NOT VALIDATED').replaceAll('_', ' ')}
          </p>
          <div className="flex items-center space-x-2 mt-2 flex-wrap gap-2">
            <span className={`text-[11px] ${muted} font-semibold`}>Configured Exam Scope:</span>
            <span className="px-2.5 py-0.5 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 rounded font-mono text-[11px] font-bold">
              Active Units: {paper.selected_units_json?.length ? paper.selected_units_json.join(', ') : 'All configured'}
            </span>
            {canEditUnits && (
              <button
                type="button"
                onClick={openEditUnits}
                className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg text-xs font-semibold border border-slate-300 dark:border-slate-600 transition flex items-center gap-1.5 shadow-sm"
                title="Change active units for this paper scrutiny"
              >
                <Sliders className="w-3.5 h-3.5 text-adcet-navy" />
                <span>Change Units</span>
              </button>
            )}
            {(paper.instructions_json || []).length > 0 && (
              <span className="px-2.5 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 rounded text-[11px] font-semibold">
                {(paper.instructions_json || []).length} paper instructions filtered
              </span>
            )}
          </div>
        </div>

        {/* Scrutiny Score Card */}
        <div className="flex items-center space-x-4 bg-slate-50/80 p-4 rounded-xl border border-slate-200">
          <div>
            <p className={`text-[10px] font-bold uppercase tracking-wider ${muted}`}>
              {report?.evidence_coverage_pct != null && report.evidence_coverage_pct < 100 ? 'Partial Scrutiny Score' : 'Scrutiny Score'}
            </p>
            <p className="text-2xl font-black text-adcet-red">
              {displayScore !== null && displayScore !== undefined ? Number(displayScore).toFixed(1) : '—'}
              {displayScore !== null && displayScore !== undefined && <span className={`text-xs font-normal ${muted}`}>/100</span>}
            </p>
            {report?.evidence_coverage_pct != null && report.evidence_coverage_pct < 100 && (
              <p className="text-[10px] text-amber-700">{report.evidence_coverage_pct}% of scoring checks evaluated</p>
            )}
          </div>
          <div className="h-8 w-px bg-slate-200 dark:bg-slate-800" />
          <div>
            <p className={`text-[10px] font-bold uppercase tracking-wider ${muted}`}>Solving Time</p>
            <p className="text-sm font-bold text-slate-900">
              {roundVal(report?.solving_time_minutes) || '—'} mins
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-slate-200 overflow-x-auto pb-2">
        {tabs.map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-brand-600 text-white shadow-lg shadow-brand-600/20'
                  : 'bg-white/60 text-slate-500 hover:text-slate-900 dark:hover:text-white border border-slate-200 dark:border-transparent'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{t.label}</span>
              {t.badge && (
                <span className="ml-1.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300">
                  {t.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* TAB 1: OVERVIEW & EXPORTS */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {pipelineError && (
            <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-600 dark:text-rose-400 text-xs">
              {pipelineError}
            </div>
          )}

          {report?.analysis_notice && (
            <div className="p-4 bg-sky-50 border border-sky-200 rounded-xl text-xs text-sky-900">
              <strong>Analysis method:</strong> {report.analysis_notice}
            </div>
          )}

          {paper.validation_status !== 'VALID_MATCH' && (
            <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-900">
              <strong>Scrutiny is blocked:</strong> this document did not pass subject validation. Review the validation evidence and upload the correct paper before analysis.
              <p className="mt-1">{paper.validation_details?.message || 'This record has no passing subject-validation result.'}</p>
            </div>
          )}

          {!report && (
            <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-700 dark:text-amber-400 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <span>
                Scrutiny report not generated yet (status: <strong>{paper.status}</strong>).
                {paper.status === 'EXTRACTION_FAILED'
                  ? ' Extraction failed — usually a scanned/image PDF. Upload a text-searchable PDF or DOCX.'
                  : paper.validation_status === 'VALID_MATCH'
                  ? ' Click Run Scrutiny to execute automated AI analysis and rule validation.'
                  : ' A passing subject-validation result is required before analysis can run.'}
              </span>
              {paper.status !== 'EXTRACTION_FAILED' && paper.validation_status === 'VALID_MATCH' && (
                <button
                  type="button"
                  onClick={runScrutinyNow}
                  disabled={runningScrutiny}
                  className="inline-flex items-center px-3 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold disabled:opacity-50 shrink-0"
                >
                  {runningScrutiny ? <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <PlayCircle className="w-3.5 h-3.5 mr-1.5" />}
                  {runningScrutiny ? 'Running…' : 'Run Scrutiny'}
                </button>
              )}
            </div>
          )}

          {/* Quick Feedback Highlight for Faculty */}
          {activeReview && (
            <div
              className={`p-5 rounded-2xl border transition-all shadow-sm ${
                activeReview.decision === 'APPROVED'
                  ? 'bg-emerald-50/90 dark:bg-emerald-950/20 border-emerald-500/40'
                  : activeReview.decision === 'MODIFICATION_REQUIRED'
                  ? 'bg-amber-50/90 dark:bg-amber-950/20 border-amber-500/40 ring-1 ring-amber-500/20'
                  : activeReview.decision === 'REJECTED'
                  ? 'bg-rose-50/90 dark:bg-rose-950/20 border-rose-500/40'
                  : 'bg-slate-50/90 dark:bg-slate-900/40 border-slate-400/40'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-black/5 dark:border-white/5">
                <div className="flex items-center space-x-2.5">
                  <div
                    className={`p-2 rounded-xl shrink-0 ${
                      activeReview.decision === 'APPROVED'
                        ? 'bg-emerald-500 text-white'
                        : activeReview.decision === 'MODIFICATION_REQUIRED'
                        ? 'bg-amber-500 text-white'
                        : activeReview.decision === 'REJECTED'
                        ? 'bg-rose-500 text-white'
                        : 'bg-slate-600 text-white'
                    }`}
                  >
                    {activeReview.decision === 'APPROVED' ? (
                      <CheckCircle2 className="w-4 h-4" />
                    ) : activeReview.decision === 'MODIFICATION_REQUIRED' ? (
                      <AlertTriangle className="w-4 h-4" />
                    ) : activeReview.decision === 'REJECTED' ? (
                      <XCircle className="w-4 h-4" />
                    ) : (
                      <AlertCircle className="w-4 h-4" />
                    )}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                      <span>
                        {activeReview.decision === 'APPROVED'
                          ? 'Question Paper Approved by Chief Moderator'
                          : activeReview.decision === 'MODIFICATION_REQUIRED'
                          ? 'Changes / Modifications Requested by Chief Moderator'
                          : activeReview.decision === 'REJECTED'
                          ? 'Question Paper Rejected by Chief Moderator'
                          : 'Review Declined by Chief Moderator'}
                      </span>
                    </h3>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">
                      Reviewed by {activeReview.moderator_name || 'Chief Examination Moderator'}
                      {activeReview.created_at ? ` • ${new Date(activeReview.created_at).toLocaleString()}` : ''}
                    </p>
                  </div>
                </div>
                <Badge status={activeReview.decision} />
              </div>

              <div className="mt-3 space-y-2">
                <div className="p-3.5 bg-white/80 dark:bg-slate-900/60 rounded-xl border border-black/5 dark:border-white/10 shadow-xs">
                  <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 mb-1 flex items-center gap-1.5">
                    <MessageSquare className="w-3.5 h-3.5 text-adcet-navy" />
                    <span>Moderator Feedback & Observations:</span>
                  </div>
                  <p className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-wrap font-medium">
                    &ldquo;{activeReview.remarks || 'No detailed written remarks.'}&rdquo;
                  </p>
                </div>

                {activeReview.required_action && (
                  <div className="p-2.5 rounded-xl bg-indigo-50/80 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800/40 text-[11px] text-indigo-900 dark:text-indigo-200 flex items-start gap-2">
                    <span className="font-bold shrink-0">Required Action:</span>
                    <span>{activeReview.required_action}</span>
                  </div>
                )}

                {activeReview.decision === 'MODIFICATION_REQUIRED' && (
                  <p className="text-[11px] text-amber-700 dark:text-amber-400 font-medium">
                    💡 Please revise your question paper document according to the moderator remarks and re-upload an updated paper.
                  </p>
                )}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className={`${panel} space-y-2`}>
              <p className={`text-xs font-semibold ${muted}`}>Compliance Summary</p>
              <p className="text-sm text-slate-800 dark:text-slate-200">
                {report?.compliance_summary || 'Analysis complete. Review question breakdown and rule validation.'}
              </p>
            </div>
            <div className={`${panel} space-y-2`}>
              <p className={`text-xs font-semibold ${muted}`}>Report Version</p>
              <p className="text-xl font-bold text-slate-900">Version {report?.version ?? 1}</p>
              <p className={`text-xs ${muted}`}>{analyzableQuestions.length} examination questions</p>
            </div>
            <div className={`${panel} space-y-2`}>
              <p className={`text-xs font-semibold ${muted}`}>Export Official Report</p>
              <div className="flex space-x-2 pt-1">
                <button
                  disabled={!report || downloadingFormat === 'pdf'}
                  onClick={() => handleDownload('pdf')}
                  className="px-3 py-1.5 bg-rose-600/15 hover:bg-rose-600 text-rose-700 dark:text-rose-300 hover:text-white rounded-lg border border-rose-500/30 text-xs font-semibold flex items-center disabled:opacity-40 transition-colors"
                >
                  {downloadingFormat === 'pdf' ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> : <Download className="w-3.5 h-3.5 mr-1" />}
                  PDF
                </button>
                <button
                  disabled={!report || downloadingFormat === 'csv'}
                  onClick={() => handleDownload('csv')}
                  className="px-3 py-1.5 bg-emerald-600/15 hover:bg-emerald-600 text-emerald-700 dark:text-emerald-300 hover:text-white rounded-lg border border-emerald-500/30 text-xs font-semibold flex items-center disabled:opacity-40 transition-colors"
                >
                  {downloadingFormat === 'csv' ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> : <Download className="w-3.5 h-3.5 mr-1" />}
                  CSV
                </button>
                <button
                  disabled={!report || downloadingFormat === 'json'}
                  onClick={() => handleDownload('json')}
                  className="px-3 py-1.5 bg-indigo-600/15 hover:bg-indigo-600 text-indigo-700 dark:text-indigo-300 hover:text-white rounded-lg border border-indigo-500/30 text-xs font-semibold flex items-center disabled:opacity-40 transition-colors"
                >
                  {downloadingFormat === 'json' ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> : <Download className="w-3.5 h-3.5 mr-1" />}
                  JSON
                </button>
              </div>
            </div>
          </div>

          {/* Extraction Debug */}
          <div className={panel}>
            <button
              type="button"
              onClick={() => setShowDebug((v) => !v)}
              className="w-full flex items-center justify-between text-left"
            >
              <span className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Bug className="w-4 h-4 text-brand-600" /> Extraction Debug
              </span>
              {showDebug ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
            {showDebug && (
              <div className="mt-4 space-y-4 text-xs">
                <div>
                  <p className={`font-semibold mb-1 ${muted}`}>Paper Instructions (filtered, not questions)</p>
                  <pre className="p-3 rounded-xl bg-slate-50 border border-slate-200 whitespace-pre-wrap max-h-40 overflow-auto text-slate-700">
                    {(paper.instructions_json || []).join('\n') || 'None detected'}
                  </pre>
                </div>
                <div>
                  <p className={`font-semibold mb-1 ${muted}`}>Raw extracted text</p>
                  <pre className="p-3 rounded-xl bg-slate-50 border border-slate-200 whitespace-pre-wrap max-h-48 overflow-auto text-slate-700">
                    {paper.raw_text || 'Not stored for this paper'}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: QUESTION BREAKDOWN */}
      {activeTab === 'breakdown' && (
        <div className={`${panel} space-y-4`}>
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <h2 className="text-base font-bold text-slate-900">Parsed Questions & Extracted Features</h2>
            <p className={`text-xs ${muted}`}>General instructions excluded. Missing marks show as —</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
                <tr>
                  <th className="p-3">Q.No</th>
                  <th className="p-3">Question Text</th>
                  <th className="p-3">Marks</th>
                  <th className="p-3">Section</th>
                  <th className="p-3">Bloom</th>
                  <th className="p-3">CO</th>
                  <th className="p-3">Unit</th>
                  <th className="p-3">Topic</th>
                  <th className="p-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 text-slate-700">
                {groupedRows.map((q) => {
                  const isGroup = (q.question_type || '').toUpperCase() === 'QUESTION_GROUP';
                  const isSub = (q.question_type || '').toUpperCase() === 'SUBQUESTION' || !!q.sub_question;
                  const bloomF = findingFor(q.id, 'BLOOM');
                  const coF = findingFor(q.id, 'CO');
                  const sylF = findingFor(q.id, 'SYLLABUS');
                  const conf = confidenceLabel(q.parse_confidence);
                  const lowConf = q.parse_confidence != null && q.parse_confidence < 0.75;

                  if (isGroup) {
                    const open = expandedGroups[q.id] !== false;
                    return (
                      <tr key={q.id} className="bg-slate-50/80 dark:bg-slate-950/50">
                        <td className="p-3 font-mono font-bold text-adcet-red" colSpan={2}>
                          <button
                            type="button"
                            className="inline-flex items-center gap-1"
                            onClick={() => setExpandedGroups((prev) => ({ ...prev, [q.id]: !open }))}
                          >
                            {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                            {q.question_number}
                            <span className="ml-2 font-sans font-medium text-slate-500 normal-case">
                              {q.question_text}
                            </span>
                          </button>
                        </td>
                        <td className="p-3 font-semibold">{formatMarks(q.marks)}{q.marks != null ? ' (group)' : ''}</td>
                        <td className="p-3" colSpan={6}>
                          <Badge variant="info">QUESTION_GROUP</Badge>
                        </td>
                      </tr>
                    );
                  }

                  return (
                    <tr key={q.id} className="hover:bg-slate-50">
                      <td className={`p-3 font-mono font-bold text-adcet-red ${isSub ? 'pl-8' : ''}`}>
                        {q.question_number}
                      </td>
                      <td className="p-3 max-w-xl">
                        <div>{q.question_text}</div>
                        {lowConf && (
                          <p className="mt-1 text-[10px] text-amber-600 dark:text-amber-400 font-semibold">
                            Low extraction confidence — moderator review recommended.
                          </p>
                        )}
                        {q.internal_choice && (
                          <span className="inline-block mt-1 text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/30">
                            Internal choice
                          </span>
                        )}
                      </td>
                      <td className="p-3 font-semibold">
                        {q.marks != null ? `${q.marks}` : <span className="text-slate-400">—</span>}
                      </td>
                      <td className="p-3">{q.section_name || 'GENERAL'}</td>
                      <td className="p-3">{q.bloom_level || bloomF?.ai_value || '—'}</td>
                      <td className="p-3">{q.co_code || coF?.ai_value || '—'}</td>
                      <td className="p-3">
                        {q.detected_unit_number != null ? `Unit ${q.detected_unit_number}` : '—'}
                        {q.unit_validation_status === 'UNSELECTED_UNIT' && (
                          <span className="block text-[10px] text-rose-600 dark:text-rose-400 font-semibold">
                            Unselected unit
                          </span>
                        )}
                      </td>
                      <td className="p-3 max-w-[10rem] truncate">{q.topic_name || sylF?.ai_value || '—'}</td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded border text-[10px] font-bold ${conf.cls}`}>{conf.text}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: BLOOM & CO MAPPING */}
      {activeTab === 'bloom' && (
        <div className={`${panel} space-y-4`}>
          <h2 className="text-base font-bold text-slate-900">Bloom&apos;s Taxonomy & Course Outcome Mapping</h2>
          <div className="space-y-3">
            {analyzableQuestions.map((q) => {
              const bloomF = findingFor(q.id, 'BLOOM');
              const coF = findingFor(q.id, 'CO');
              return (
                <div key={q.id} className="p-4 bg-slate-50/60 border border-slate-200 rounded-xl space-y-2">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <span className="font-mono font-bold text-adcet-red text-sm">
                      {q.question_number} ({q.marks != null ? `${q.marks} Marks` : 'Marks not detected'})
                    </span>
                    <div className="flex space-x-2">
                      <span className="px-2.5 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-700 dark:text-blue-400 rounded text-xs font-bold">
                        Bloom: {q.bloom_level || bloomF?.ai_value || '—'}
                      </span>
                      <span className="px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400 rounded text-xs font-bold">
                        CO: {q.co_code || coF?.ai_value || '—'}
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-slate-700">{q.question_text}</p>
                  <p className={`text-[11px] ${muted} italic`}>
                    Evidence: {bloomF?.reasoning || coF?.reasoning || 'Cognitive analysis rationale.'}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 4: GRAMMAR & QUALITY */}
      {activeTab === 'grammar' && (
        <div className={`${panel} space-y-4`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-200">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <Sliders className="w-4 h-4 text-adcet-navy" />
                <span>Automatic Grammar &amp; Language Quality Evaluation</span>
              </h2>
              <p className={`text-xs ${muted} mt-0.5`}>
                Evaluated through Google Gemini API with fallback linguistic analysis. Identifies grammar, spelling, punctuation, sentence clarity, and ambiguous questions.
              </p>
            </div>
            <div className="p-2 bg-indigo-50 border border-indigo-200 rounded-xl text-[11px] text-indigo-800 font-semibold flex items-center gap-1.5 shrink-0">
              <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
              <span>Advisory Suggestions — Original Paper Unchanged</span>
            </div>
          </div>

          <div className="space-y-4">
            {analyzableQuestions.map((q) => {
              const gramF = findingFor(q.id, 'GRAMMAR');
              const qualF = findingFor(q.id, 'QUALITY');
              const structuredIssues = Array.isArray(gramF?.issues) ? gramF.issues : [];

              return (
                <div key={q.id} className="p-4 bg-slate-50/60 border border-slate-200 rounded-xl space-y-3">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-adcet-red text-xs px-2 py-0.5 rounded bg-white border border-slate-200">
                        {q.question_number}
                      </span>
                      <span className="text-xs text-slate-600 font-medium">({formatMarks(q.marks)} Marks)</span>
                    </div>
                    <div className="flex gap-2">
                      <Badge status={gramF?.ai_value || 'NOT_EVALUATED'}>Grammar: {gramF?.ai_value || 'NOT_EVALUATED'}</Badge>
                      <Badge status={qualF?.ai_value || 'NOT_EVALUATED'}>Quality: {qualF?.ai_value || 'NOT_EVALUATED'}</Badge>
                    </div>
                  </div>

                  <div className="p-3 bg-white rounded-lg border border-slate-200 text-xs text-slate-800 leading-relaxed font-sans">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">Original Question Text:</span>
                    {q.question_text}
                  </div>

                  {gramF?.reasoning && (
                    <p className="text-[11px] text-slate-600 italic">
                      <span className="font-semibold text-slate-700 not-italic">Evaluation Summary: </span>{gramF.reasoning}
                    </p>
                  )}

                  {/* Structured Issues Identified */}
                  {structuredIssues.length > 0 && (
                    <div className="space-y-2 pt-1">
                      <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block">
                        Identified Quality &amp; Language Issues ({structuredIssues.length}):
                      </span>
                      <div className="grid grid-cols-1 gap-2">
                        {structuredIssues.map((issue, idx) => (
                          <div key={idx} className="p-3 bg-white rounded-xl border border-slate-200 space-y-2 shadow-xs">
                            <div className="flex items-center justify-between flex-wrap gap-2">
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-purple-500/10 text-purple-700 border border-purple-500/30">
                                {issue.category || issue.issue_type || 'Language Issue'}
                              </span>
                              <span className="text-[10px] text-slate-400 font-medium">Faculty Review Requested</span>
                            </div>

                            {issue.original_text && (
                              <div className="text-xs">
                                <span className="font-semibold text-slate-500">Problematic Phrase: </span>
                                <code className="bg-rose-50 text-rose-800 px-1.5 py-0.5 rounded border border-rose-200 font-mono text-[11px]">
                                  {issue.original_text}
                                </code>
                              </div>
                            )}

                            {(issue.problem || issue.explanation) && (
                              <div className="text-xs text-slate-700">
                                <span className="font-semibold text-slate-900">Identified Issue: </span>
                                {issue.problem || issue.explanation}
                              </div>
                            )}

                            {issue.suggested_correction && (
                              <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs space-y-0.5">
                                <span className="font-semibold text-emerald-800">Suggested Correction: </span>
                                <p className="text-slate-900 font-medium">{issue.suggested_correction}</p>
                              </div>
                            )}

                            {issue.explanation && issue.problem && (
                              <p className="text-[11px] text-slate-500 italic">
                                <span className="font-medium not-italic text-slate-600">Details: </span>{issue.explanation}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Fallback suggested improvement if no structured items */}
                  {structuredIssues.length === 0 && gramF?.suggested_improvement && (
                    <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs space-y-1">
                      <p className="font-semibold text-amber-700">Suggested Phrasing Improvement:</p>
                      <p className="text-slate-800">{gramF.suggested_improvement}</p>
                    </div>
                  )}

                  {/* Clean phrasing indicator */}
                  {structuredIssues.length === 0 && !gramF?.suggested_improvement && (gramF?.ai_value === 'CLEAN' || gramF?.ai_value === 'PASS') && (
                    <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs text-emerald-800 flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span>Clean wording and correct grammar. No language quality or ambiguity issues detected.</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 5: SIMILARITY FLAGS */}
      {activeTab === 'similarity' && (
        <div className={`${panel} space-y-4`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-200">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-adcet-red" />
                <span>Question Similarity &amp; Repetition Detection</span>
              </h2>
              <p className={`text-xs ${muted} mt-0.5`}>
                Compares questions across historical exam papers, peer submissions, and internal repetitions within this paper.
              </p>
            </div>
            <div className="p-2 bg-amber-50 border border-amber-200 rounded-xl text-[11px] text-amber-800 font-semibold flex items-center gap-1.5 shrink-0">
              <ShieldCheck className="w-3.5 h-3.5 text-amber-600" />
              <span>Indicative Matching — Requires Academic Review</span>
            </div>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-600 leading-relaxed">
            <strong>Institutional Policy Note:</strong> Text similarity flags identify potential question overlap or reuse across academic cycles. High similarity does not automatically establish plagiarism or academic misconduct; human moderator verification is required.
          </div>

          {!report?.similarity_results?.length ? (
            <div className="p-8 text-center bg-slate-50 rounded-2xl border border-dashed border-slate-200 space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
              <p className="font-bold text-slate-900 text-xs">No Significant Similarity Flags Detected</p>
              <p className="text-[11px] text-slate-500 max-w-md mx-auto">
                {report?.rule_results?.find((rule) => rule.rule_name === 'Previous Paper Similarity Check')?.message || 'All questions fall below the similarity threshold against historical archives, peer submissions, and internal paper sections.'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {report.similarity_results.map((s, idx) => {
                const isInternal = s.explanation?.toLowerCase().includes('in-paper duplicate') || s.explanation?.toLowerCase().includes('same paper');
                const pct = (s.similarity_score * 100).toFixed(1);
                const scoreNum = s.similarity_score * 100;

                return (
                  <div key={s.id || idx} className="p-4 bg-white border border-slate-200 rounded-xl space-y-3 shadow-xs">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-adcet-navy text-xs px-2.5 py-1 rounded-lg bg-slate-100 border border-slate-200">
                          {s.question_number ? `Question ${s.question_number}` : `Question Index #${idx + 1}`}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          isInternal
                            ? 'bg-purple-500/10 text-purple-700 border border-purple-500/30'
                            : 'bg-amber-500/10 text-amber-700 border border-amber-500/30'
                        }`}>
                          {isInternal ? 'Internal In-Paper Duplicate' : 'Historical Paper Comparison'}
                        </span>
                      </div>

                      <div className="flex items-center gap-3">
                        <span className={`font-mono text-xs font-bold ${
                          scoreNum >= 85 ? 'text-rose-700' : scoreNum >= 75 ? 'text-amber-700' : 'text-blue-700'
                        }`}>
                          {pct}% Similarity
                        </span>
                        <div className="w-20 h-2 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
                          <div
                            className={`h-full rounded-full ${scoreNum >= 85 ? 'bg-rose-500' : scoreNum >= 75 ? 'bg-amber-500' : 'bg-blue-500'}`}
                            style={{ width: `${Math.min(scoreNum, 100)}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    {s.matched_paper_title && (
                      <div className="flex items-center gap-2 p-2.5 bg-amber-50/80 border border-amber-200 rounded-lg text-xs text-amber-900 font-medium">
                        <FileText className="w-4 h-4 text-amber-600 shrink-0" />
                        <span className="text-slate-600 font-semibold">Matched Question Paper:</span>
                        <span className="font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-amber-200/80 shadow-2xs">
                          {s.matched_paper_title}
                        </span>
                      </div>
                    )}

                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-800 leading-relaxed">
                      <span className="font-semibold text-slate-700 block mb-0.5">Similarity Finding &amp; Comparison:</span>
                      {s.explanation}
                    </div>

                    {s.matched_question_text && (
                      <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 space-y-1">
                        <span className="text-[10px] uppercase font-bold text-slate-500 block">
                          Matched Archival Question:
                        </span>
                        <p className="italic text-slate-800 font-serif">
                          &ldquo;{s.matched_question_text}&rdquo;
                        </p>
                      </div>
                    )}

                    <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-100">
                      <span>Status: Flagged for Chief Moderator Review</span>
                      <span className="text-slate-400">TF-IDF Vector &amp; Token Overlap Model</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 6: RULE VALIDATION */}
      {activeTab === 'rules' && (
        <div className={`${panel} space-y-4`}>
          <h2 className="text-base font-bold text-slate-900">Deterministic Rule Engine Results</h2>
          {!report?.rule_results?.length ? (
            <p className={`text-xs ${muted}`}>No rule results available yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
                  <tr>
                    <th className="p-3">Category</th>
                    <th className="p-3">Rule Name</th>
                    <th className="p-3">Expected</th>
                    <th className="p-3">Actual</th>
                    <th className="p-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 text-slate-700">
                  {report.rule_results.map((r) => (
                    <tr key={r.id ?? r.rule_name} className="hover:bg-slate-50">
                      <td className={`p-3 font-semibold ${muted}`}>{r.category}</td>
                      <td className="p-3 font-bold text-slate-900">{r.rule_name}</td>
                      <td className={`p-3 ${muted}`}>{r.expected_value}</td>
                      <td className="p-3 font-mono">{r.actual_value}</td>
                      <td className="p-3">
                        <Badge status={r.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 7: MODERATOR REVIEW ROOM (OR FACULTY FEEDBACK VIEW) */}
      {activeTab === 'decision' && (
        <div className="space-y-6">
          {successMsg && (
            <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-700 dark:text-emerald-400 text-xs flex items-center">
              <CheckCircle2 className="w-4 h-4 mr-2" />
              <span>{successMsg}</span>
            </div>
          )}

          {errorMsg && (
            <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-700 dark:text-rose-400 text-xs flex items-center">
              <AlertTriangle className="w-4 h-4 mr-2" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* FACULTY VIEW: Dedicated Moderator Feedback Display */}
          {!isModeratorOrAdmin && (
            <div className={`${panel} space-y-5`}>
              <div className="flex items-center justify-between border-b border-slate-200 pb-4">
                <div>
                  <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
                    <ShieldCheck className="w-5 h-5 text-adcet-navy" />
                    <span>Chief Moderator Feedback &amp; Official Decision</span>
                  </h2>
                  <p className={`text-xs ${muted} mt-0.5`}>
                    Institutional evaluation and binding action issued by the examination moderation cell.
                  </p>
                </div>
                {activeReview ? (
                  <Badge status={activeReview.decision} />
                ) : (
                  <Badge variant="warning">PENDING REVIEW</Badge>
                )}
              </div>

              {activeReview ? (
                <div className="space-y-4 text-xs">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 bg-slate-50/80 rounded-xl border border-slate-200 space-y-1">
                      <span className="text-slate-500 font-medium">Chief Moderator:</span>
                      <p className="font-bold text-slate-900 text-sm">
                        {activeReview.moderator_name || 'Chief Examination Moderator'}
                      </p>
                      <p className="text-[11px] text-slate-500">Examination Moderation Committee</p>
                    </div>

                    <div className="p-4 bg-slate-50/80 rounded-xl border border-slate-200 space-y-1">
                      <span className="text-slate-500 font-medium">Review Date &amp; Time:</span>
                      <p className="font-bold text-slate-900">
                        {activeReview.created_at ? new Date(activeReview.created_at).toLocaleString() : 'Recent'}
                      </p>
                      <p className="text-[11px] text-slate-500">Official Decision Recorded in System</p>
                    </div>
                  </div>

                  <div className={`p-4 rounded-xl border space-y-2 ${
                    activeReview.decision === 'APPROVED'
                      ? 'bg-emerald-500/10 border-emerald-500/30'
                      : activeReview.decision === 'MODIFICATION_REQUIRED'
                      ? 'bg-amber-500/10 border-amber-500/30'
                      : activeReview.decision === 'REJECTED'
                      ? 'bg-rose-500/10 border-rose-500/30'
                      : 'bg-slate-500/10 border-slate-500/30'
                  }`}>
                    <span className="font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-1.5">
                      <MessageSquare className="w-4 h-4 text-adcet-navy" />
                      <span>Moderator Remarks &amp; Feedback:</span>
                    </span>
                    <p className="text-slate-800 dark:text-slate-200 text-xs leading-relaxed whitespace-pre-wrap bg-white dark:bg-slate-900/60 p-3 rounded-lg border border-slate-200/60 dark:border-slate-800 font-medium">
                      {activeReview.remarks || 'No detailed written remarks.'}
                    </p>
                  </div>

                  {activeReview.required_action && (
                    <div className="p-4 bg-indigo-500/10 border border-indigo-500/30 rounded-xl space-y-1">
                      <span className="font-bold text-indigo-700 dark:text-indigo-400">Required Action for Faculty:</span>
                      <p className="text-slate-800 dark:text-slate-200 text-xs leading-relaxed">
                        {activeReview.required_action}
                      </p>
                    </div>
                  )}

                  {activeReview.decision === 'MODIFICATION_REQUIRED' && (
                    <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-amber-800 flex items-start space-x-2">
                      <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-600" />
                      <div className="text-[11px] leading-relaxed">
                        <span className="font-semibold">Action for Faculty:</span> The Chief Moderator has requested revisions. Please update the questions or formatting according to the feedback above and re-upload the revised question paper.
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-8 text-center bg-slate-50/50 rounded-xl border border-dashed border-slate-300 dark:border-slate-800 space-y-2">
                  <Clock className="w-8 h-8 text-amber-500 mx-auto" />
                  <p className="font-bold text-slate-800 dark:text-slate-200 text-xs">Awaiting Chief Moderator Evaluation</p>
                  <p className="text-[11px] text-slate-500 max-w-md mx-auto">
                    Your question paper has completed automated AI scrutiny and rule verification. The Chief Moderator has been queued to review your paper and issue the official institutional decision.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* MODERATOR & ADMIN VIEW: Interactive Submission Form */}
          {isModeratorOrAdmin && paper.validation_status === 'VALID_MATCH' && report && (
            <form onSubmit={handleOpenConfirm} className={`${panel} space-y-6`}>
              <div>
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <h2 className="text-base font-bold text-slate-900">
                    Human Moderator Official Supervision &amp; Decision
                  </h2>
                  {activeReview && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500 font-medium">Current Status:</span>
                      <Badge status={activeReview.decision} />
                    </div>
                  )}
                </div>
                <p className={`text-xs ${muted} mt-1`}>
                  Review AI findings, override where needed, record detailed observations, and confirm the official institutional decision.
                </p>
                {activeReview && (
                  <div className="mt-3 p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1">
                    <p className="font-semibold text-slate-800">
                      Previously saved review by {activeReview.moderator_name || 'Chief Moderator'}:
                    </p>
                    <p className="italic text-slate-700 bg-white p-2 rounded border border-slate-200/80">
                      &quot;{activeReview.remarks}&quot;
                    </p>
                    {activeReview.required_action && (
                      <p className="text-[11px] text-slate-500">Action: {activeReview.required_action}</p>
                    )}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-2">
                  Paper Decision Option *
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {[
                    { key: 'APPROVED', label: '1. APPROVE', desc: 'Approve paper for examination cell', Icon: CheckCircle2, active: 'bg-emerald-600 text-white border-emerald-500 shadow-md ring-2 ring-emerald-500/20' },
                    { key: 'MODIFICATION_REQUIRED', label: '2. REQUEST CHANGES', desc: 'Require modifications or changes to paper', Icon: AlertTriangle, active: 'bg-amber-600 text-white border-amber-500 shadow-md ring-2 ring-amber-500/20' },
                    { key: 'REJECTED', label: '3. REJECT', desc: 'Reject paper and record reason', Icon: XCircle, active: 'bg-rose-600 text-white border-rose-500 shadow-md ring-2 ring-rose-500/20' },
                  ].map(({ key, label, desc, Icon, active }) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setDecision(key)}
                      className={`p-3.5 rounded-xl border font-bold text-xs transition-all text-left flex flex-col justify-between cursor-pointer ${
                        decision === key ? active : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                      }`}
                    >
                      <div className="flex items-center space-x-2">
                        <Icon className="w-4 h-4 shrink-0" />
                        <span className="font-bold">{label}</span>
                      </div>
                      <span className={`text-[10px] font-normal mt-1.5 ${decision === key ? 'text-white/80' : 'text-slate-400'}`}>
                        {desc}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Moderator Detailed Feedback, Observations &amp; Suggestions *
                </label>
                <textarea
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  rows={4}
                  required
                  placeholder="Enter detailed feedback, observations, corrections, and suggestions for the faculty member..."
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-900 focus:outline-none focus:border-brand-600"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Faculty will only be able to view this feedback after you confirm and submit your official decision.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Required Action for Faculty (Optional)
                </label>
                <input
                  type="text"
                  value={requiredAction}
                  onChange={(e) => setRequiredAction(e.target.value)}
                  placeholder="e.g. Please revise Q3 to balance cognitive levels with Course Outcome CO2."
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-xs text-slate-900 focus:outline-none focus:border-brand-600"
                />
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full bg-adcet-navy hover:bg-slate-800 text-white font-semibold py-3 rounded-xl transition-all shadow-lg text-xs disabled:opacity-50 flex items-center justify-center space-x-2 cursor-pointer"
              >
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Submit Moderator Decision &amp; Feedback</span>
              </button>
            </form>
          )}
          {isModeratorOrAdmin && paper.validation_status !== 'VALID_MATCH' && (
            <div role="status" className={`${panel} border-rose-200 text-xs leading-relaxed text-rose-900`}>
              Moderator decisions are unavailable because this record has no passing validation result. Inspect the validation evidence, then ask faculty to upload a subject-matched paper.
            </div>
          )}
          {isModeratorOrAdmin && paper.validation_status === 'VALID_MATCH' && !report && paper.status !== 'FAILED' && paper.status !== 'EXTRACTION_FAILED' && (
            <div role="status" className={`${panel} text-center py-8 space-y-4`}>
              <div className="w-12 h-12 rounded-2xl bg-amber-500/10 text-amber-600 flex items-center justify-center mx-auto">
                <Clock className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-slate-900">Scrutiny Report Pending</h3>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  A moderator decision becomes available after a scrutiny report has been generated. You can trigger automated rule verification, Gemini language evaluation, and similarity checks now.
                </p>
              </div>
              <button
                type="button"
                onClick={runScrutinyNow}
                disabled={runningScrutiny}
                className="px-5 py-2.5 bg-adcet-navy hover:bg-slate-800 text-white text-xs font-bold rounded-xl shadow transition-all inline-flex items-center gap-2 disabled:opacity-50"
              >
                {runningScrutiny ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Executing Scrutiny Pipeline...</span>
                  </>
                ) : (
                  <>
                    <PlayCircle className="w-4 h-4 text-emerald-400" />
                    <span>Run Scrutiny Analysis Now</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}
      {/* EDIT EXAM UNITS MODAL */}
      {editingUnitsOpen && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-adcet-navy/10 flex items-center justify-center text-adcet-navy">
                  <Sliders className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 dark:text-white text-base">Select Exam Units</h3>
                  <p className="text-xs text-slate-500">Choose which syllabus units this examination covers</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setEditingUnitsOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-lg"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-600 dark:text-slate-400">
                  {tempUnits.length} of {subjectUnits.length} unit(s) selected
                </span>
                <div className="flex gap-2 text-xs">
                  <button
                    type="button"
                    onClick={() => setTempUnits(subjectUnits.map((u) => u.unit_number))}
                    className="text-adcet-navy hover:underline font-semibold"
                  >
                    Select All
                  </button>
                  <span className="text-slate-300">|</span>
                  <button
                    type="button"
                    onClick={() => setTempUnits([])}
                    className="text-slate-500 hover:underline"
                  >
                    Clear All
                  </button>
                </div>
              </div>

              {subjectUnits.length === 0 ? (
                <p className="text-xs text-slate-500 py-4 text-center">
                  No syllabus units found for this subject.
                </p>
              ) : (
                <div className="max-h-60 overflow-y-auto space-y-2 pr-1">
                  {subjectUnits.map((u) => {
                    const isChecked = tempUnits.includes(u.unit_number);
                    return (
                      <label
                        key={u.unit_number}
                        className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition ${
                          isChecked
                            ? 'bg-emerald-500/10 border-emerald-500/40 text-slate-900 dark:text-white'
                            : 'bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-300'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => {
                            setTempUnits((prev) =>
                              prev.includes(u.unit_number)
                                ? prev.filter((num) => num !== u.unit_number)
                                : [...prev, u.unit_number].sort((a, b) => a - b)
                            );
                          }}
                          className="mt-0.5 rounded text-adcet-navy focus:ring-adcet-navy"
                        />
                        <div className="text-xs">
                          <span className="font-bold">Unit {u.unit_number}:</span>{' '}
                          <span>{u.title || 'Untitled Unit'}</span>
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}

              <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-800 dark:text-amber-300">
                <strong>Note:</strong> Saving will update the paper&apos;s configured unit boundary and automatically re-run scrutiny analysis against the selected units.
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
              <button
                type="button"
                disabled={savingUnits}
                onClick={() => setEditingUnitsOpen(false)}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 rounded-xl transition"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={savingUnits || tempUnits.length === 0}
                onClick={handleSaveUnitsAndRescrutinize}
                className="px-4 py-2 text-xs font-semibold text-white bg-adcet-red hover:bg-red-700 disabled:opacity-50 rounded-xl transition shadow flex items-center gap-1.5"
              >
                {savingUnits ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Re-analyzing Scrutiny...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Save &amp; Re-run Scrutiny</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
      {/* CONFIRM MODERATOR DECISION MODAL */}
      <ConfirmModal
        isOpen={confirmModalOpen}
        title={
          decision === 'APPROVED'
            ? 'Confirm Paper Approval'
            : decision === 'MODIFICATION_REQUIRED'
            ? 'Confirm Changes / Modifications Request'
            : decision === 'REJECTED'
            ? 'Confirm Paper Rejection'
            : 'Confirm Decline Review'
        }
        message={
          decision === 'APPROVED'
            ? 'Are you sure you want to approve this question paper? This will confirm the scrutiny review and publish your feedback to the faculty author.'
            : decision === 'MODIFICATION_REQUIRED'
            ? 'Are you sure you want to request changes for this question paper? The recorded observations, feedback remarks, and required modifications will be published directly to the faculty author.'
            : decision === 'REJECTED'
            ? 'Are you sure you want to reject this question paper? The recorded remarks and required actions will be communicated to the faculty member for correction.'
            : 'Are you sure you want to decline this review? Your reason for declining will be recorded and published to the faculty member.'
        }
        confirmLabel={
          decision === 'APPROVED'
            ? 'Confirm Approval'
            : decision === 'MODIFICATION_REQUIRED'
            ? 'Submit Changes Request'
            : decision === 'REJECTED'
            ? 'Confirm Rejection'
            : 'Confirm Decline'
        }
        confirmVariant={decision === 'APPROVED' ? 'primary' : decision === 'MODIFICATION_REQUIRED' ? 'warning' : 'danger'}
        loading={submitting}
        onConfirm={handleSubmitDecisionConfirmed}
        onCancel={() => setConfirmModalOpen(false)}
      >
        <div className="p-3 bg-slate-50 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700 space-y-2 mt-3 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-slate-500">Official Decision:</span>
            <Badge status={decision}>{decision.replace('_', ' ')}</Badge>
          </div>
          <div>
            <span className="font-semibold text-slate-500">Target Paper:</span>
            <p className="font-bold text-slate-800 dark:text-slate-200 mt-0.5">{paper.title}</p>
          </div>
          <div>
            <span className="font-semibold text-slate-500">Recorded Observations &amp; Feedback:</span>
            <p className="text-slate-700 dark:text-slate-300 italic mt-0.5 line-clamp-3 bg-white dark:bg-slate-900 p-2 rounded border border-slate-200 dark:border-slate-800">
              &quot;{remarks}&quot;
            </p>
          </div>
          {requiredAction && (
            <div>
              <span className="font-semibold text-slate-500">Required Action for Faculty:</span>
              <p className="text-slate-700 dark:text-slate-300 mt-0.5">{requiredAction}</p>
            </div>
          )}
        </div>
      </ConfirmModal>
    </div>
  );
}
