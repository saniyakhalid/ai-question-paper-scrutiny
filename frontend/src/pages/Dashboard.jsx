import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import Badge from '../components/common/Badge';
import ScoreCard from '../components/common/ScoreCard';
import AddSubjectModal from '../components/common/AddSubjectModal';
import {
  FileText, Clock, CheckCircle2, AlertTriangle, XCircle, Award,
  ArrowUpRight, BookOpen, Layers, Folder, ShieldCheck, UploadCloud,
  ChevronRight, ArrowRight, Sliders, Plus, Search, Filter,
  GraduationCap, CheckSquare, Sparkles, ExternalLink, Loader2, Brain,
  MessageSquare, X
} from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, PieChart, Pie } from 'recharts';

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState('ALL');
  const [data, setData] = useState(null);
  const [subjectDash, setSubjectDash] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [addSubjectOpen, setAddSubjectOpen] = useState(false);
  const [feedbackModalPaper, setFeedbackModalPaper] = useState(null);
  const subjectRequestRef = useRef(0);

  const isFaculty = user?.role === 'FACULTY';
  const isModerator = user?.role === 'MODERATOR';
  const isAdmin = user?.role === 'ADMIN';

  useEffect(() => {
    fetchGlobalData();
    fetchSubjects();
  }, []);

  const fetchSubjects = (selectId = null) => {
    api.get('/subjects')
      .then((res) => {
        setSubjects(res.data || []);
        if (selectId) {
          handleSubjectChange(selectId);
        }
      })
      .catch(() => {});
  };

  const fetchGlobalData = () => {
    const requestId = ++subjectRequestRef.current;
    setLoading(true);
    api.get('/dashboard/stats')
      .then((res) => setData(res.data))
      .catch((err) => console.error('Failed to load dashboard statistics:', err))
      .finally(() => {
        if (subjectRequestRef.current === requestId) setLoading(false);
      });
  };

  const handleSubjectChange = (subjId) => {
    const requestId = ++subjectRequestRef.current;
    setSelectedSubjectId(subjId);
    if (subjId === 'ALL') {
      setSubjectDash(null);
      fetchGlobalData();
    } else {
      setSubjectDash(null);
      setLoading(true);
      api.get(`/subjects/${subjId}/dashboard`)
        .then((res) => {
          if (subjectRequestRef.current === requestId) setSubjectDash(res.data);
        })
        .catch((err) => console.error('Failed to load subject dashboard:', err))
        .finally(() => {
          if (subjectRequestRef.current === requestId) setLoading(false);
        });
    }
  };

  const handleSubjectCreated = (newSubject) => {
    fetchSubjects(newSubject.id);
  };

  const BLOOM_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#6366F1'];

  // Filter recent papers by search query if any
  const recentPapers = (data?.recent_papers || []).filter((p) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (p.title || '').toLowerCase().includes(q) ||
      (p.subject_code || '').toLowerCase().includes(q) ||
      (p.uploaded_by || '').toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10">
      {/* 1. Header Banner with Faculty / Staff Persona */}
      <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-5">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-xl font-bold text-adcet-navy">
              {isFaculty
                ? `Faculty Examination Console: ${user?.full_name || 'Faculty Member'}`
                : isModerator
                ? `Chief Moderator Supervision Console`
                : `Examination Cell Administration Console`}
            </h1>
            <Badge status={user?.role || 'FACULTY'} />
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
              {user?.department || 'Computer Science & Engineering'}
            </span>
          </div>
          <p className="text-xs text-slate-500 max-w-3xl">
            {isFaculty
              ? 'Upload papers into subject workspaces, review configured checks and analysis notices, and read moderator remarks.'
              : isModerator
              ? 'Supervise submitted examination papers, review deterministic rule engine scores, inspect similarity flags, and record official binding decisions.'
              : 'Global institutional governance over syllabus documents, question papers, and accreditation audit records.'}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          {(isFaculty || isAdmin || isModerator) && (
            <button
              type="button"
              onClick={() => setAddSubjectOpen(true)}
              className="px-3.5 py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-bold rounded-xl transition-all border border-slate-200 shadow-sm flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5 text-adcet-red" />
              <span>Add Subject</span>
            </button>
          )}

          {(isFaculty || isAdmin || isModerator) && (
            <button
              type="button"
              onClick={() => navigate('/papers/upload')}
              className="px-4 py-2 bg-adcet-red hover:bg-red-700 text-white text-xs font-bold rounded-xl transition-all shadow-md flex items-center gap-1.5"
            >
              <UploadCloud className="w-4 h-4" />
              <span>Upload Paper</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => navigate('/subjects?tab=ppt_library')}
            className="px-3.5 py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-bold rounded-xl transition-all border border-slate-200 flex items-center gap-1.5"
          >
            <Folder className="w-3.5 h-3.5 text-adcet-navy" />
            <span>PPT Upload</span>
          </button>

          {(isModerator || isAdmin) && (
            <button
              type="button"
              onClick={() => navigate('/moderator/queue')}
              className="px-3.5 py-2 bg-amber-50 hover:bg-amber-100 text-amber-800 text-xs font-bold rounded-xl transition-all border border-amber-200 flex items-center gap-1.5"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Review Queue</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => navigate('/subjects')}
            className="px-3.5 py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-bold rounded-xl transition-all border border-slate-200 flex items-center gap-1.5"
          >
            <BookOpen className="w-3.5 h-3.5 text-adcet-navy" />
            <span>Curriculum</span>
          </button>
        </div>
      </div>

      {/* 2. Workspace Filter & Search Bar */}
      <div className="bg-white border border-slate-200 px-5 py-3.5 rounded-2xl shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Subject Workspace Filter Dropdown */}
        <div className="flex items-center gap-2.5 w-full sm:w-auto">
          <div className="w-8 h-8 rounded-lg bg-red-50 text-adcet-red flex items-center justify-center shrink-0">
            <BookOpen className="w-4 h-4" />
          </div>
          <div className="flex min-w-0 flex-1 items-center gap-2 text-xs">
            <span className="text-slate-500 font-semibold shrink-0">Subject Workspace:</span>
            <select
              value={selectedSubjectId}
              onChange={(e) => handleSubjectChange(e.target.value)}
              className="min-w-0 max-w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 text-xs text-slate-900 font-bold focus:outline-none focus:border-adcet-red cursor-pointer"
            >
              <option value="ALL">All Subjects (Global Overview)</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.code} — {s.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search papers by title or code..."
            className="w-full bg-slate-50 border border-slate-200 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-800 focus:outline-none focus:border-adcet-red"
          />
        </div>
      </div>

      {/* 3. Global or Subject-Specific Metrics */}
      {selectedSubjectId !== 'ALL' ? (subjectDash ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <ScoreCard
              title="Configured Units"
              value={subjectDash.stats?.total_units || 0}
              subtitle="Active syllabus boundaries"
              icon={Layers}
              color="brand"
            />
            <ScoreCard
              title="Course Outcomes"
              value={subjectDash.stats?.total_cos || 0}
              subtitle="Configured subject outcomes"
              icon={BookOpen}
              color="emerald"
            />
            <ScoreCard
              title="Reference Documents"
              value={subjectDash.stats?.total_documents || 0}
              subtitle="Syllabus PDFs & materials"
              icon={Folder}
              color="blue"
            />
            <ScoreCard
              title="Historical Questions"
              value={subjectDash.stats?.total_previous_questions || 0}
              subtitle="From uploaded previous papers"
              icon={FileText}
              color="amber"
            />
          </div>

          <div className="bg-white border border-slate-200 p-5 rounded-2xl space-y-3 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-adcet-navy flex items-center gap-2">
                <Layers className="w-4 h-4 text-adcet-red" />
                Active Syllabus Units for Selected Subject
              </h2>
              <button
                type="button"
                onClick={() => navigate('/subjects')}
                className="text-xs font-semibold text-adcet-red hover:underline"
              >
                Manage in Curriculum →
              </button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
              {(subjectDash.units || []).map((u) => (
                <div key={u.id} className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-adcet-navy">Unit {u.unit_number}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-white text-slate-500 border border-slate-200 font-semibold">
                      {(u.topics || []).length} Topics
                    </span>
                  </div>
                  <p className="font-bold text-slate-800 text-xs truncate mt-1">
                    {u.title || `Unit ${u.unit_number}`}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Confirmed Course Outcomes (COs) Section for Selected Subject */}
          <div className="bg-white border border-slate-200 p-5 rounded-2xl space-y-3 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-adcet-navy" />
                <h2 className="text-sm font-bold text-slate-900">
                  Confirmed Course Outcomes (COs) — {subjectDash.subject?.code}
                </h2>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                  {(subjectDash.cos || []).length} COs
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => navigate('/syllabus')}
                  className="text-xs font-semibold text-adcet-red hover:underline flex items-center gap-1"
                >
                  <span>Extract from Syllabus</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
                <span className="text-slate-300">|</span>
                <button
                  type="button"
                  onClick={() => navigate('/subjects?tab=cos')}
                  className="text-xs font-semibold text-adcet-navy hover:underline"
                >
                  Manage COs →
                </button>
              </div>
            </div>

            {(!subjectDash.cos || subjectDash.cos.length === 0) ? (
              <div className="p-6 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-center space-y-2">
                <p className="text-xs text-slate-500">
                  No Course Outcomes configured or extracted for this subject yet.
                </p>
                <button
                  type="button"
                  onClick={() => navigate('/syllabus')}
                  className="px-3 py-1.5 bg-adcet-navy text-white text-xs font-semibold rounded-lg hover:bg-slate-800 transition"
                >
                  Upload Syllabus Document &amp; Extract COs
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                {subjectDash.cos.map((c, idx) => (
                  <div key={idx} className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-adcet-red bg-white px-2 py-0.5 rounded border border-slate-200 text-[11px]">
                        {c.co_code}
                      </span>
                      <span className="text-[10px] text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        Active in Scrutiny
                      </span>
                    </div>
                    <p className="text-slate-700 text-xs leading-relaxed mt-1">
                      {c.description}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm" role="status" aria-live="polite">
          <span className="inline-flex items-center gap-2">
            {loading && <Loader2 className="h-4 w-4 animate-spin text-adcet-red" />}
            {loading ? 'Loading the selected subject workspace…' : 'Could not load this subject workspace. Please try selecting it again.'}
          </span>
        </div>
      )) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <ScoreCard
            title="Total Papers"
            value={data?.cards?.total_papers || 0}
            subtitle="Institutional submissions"
            icon={FileText}
            color="brand"
          />
          <ScoreCard
            title="Avg. Scrutiny"
            value={data?.cards?.avg_scrutiny_score == null ? '—' : `${data.cards.avg_scrutiny_score}/100`}
            subtitle="Deterministic score"
            icon={Award}
            color="emerald"
          />
          <ScoreCard
            title="Pending Review"
            value={data?.cards?.pending_reviews || 0}
            subtitle="Awaiting moderator"
            icon={Clock}
            color="amber"
          />
          <ScoreCard
            title="Approved Papers"
            value={data?.cards?.approved || 0}
            subtitle="Passed quality scrutiny"
            icon={CheckCircle2}
            color="emerald"
          />
          <ScoreCard
            title="Needs Revision"
            value={data?.cards?.needs_modification || 0}
            subtitle="Feedback returned"
            icon={AlertTriangle}
            color="amber"
          />
          <ScoreCard
            title="Major Flagged"
            value={data?.cards?.rejected || 0}
            subtitle="Rule or format issues"
            icon={XCircle}
            color="rose"
          />
        </div>
      )}

      {/* 4. Structured Main Section: Left (Recent Papers) & Right (Quality Analytics) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (8 cols): Recent Question Paper Submissions */}
        <div className="lg:col-span-8 space-y-4">
          <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-adcet-red" />
                <h2 className="text-sm font-bold text-slate-900">
                  Recent Question Paper Submissions & Scrutiny Reports
                </h2>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => navigate('/papers')}
                  className="text-xs font-semibold text-adcet-navy hover:text-adcet-red flex items-center transition-colors"
                >
                  <span>All Papers</span>
                  <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/history')}
                  className="text-xs font-semibold text-adcet-navy hover:text-adcet-red flex items-center transition-colors"
                >
                  <span>Scrutiny History</span>
                  <ChevronRight className="w-3.5 h-3.5 ml-0.5" />
                </button>
              </div>
            </div>

            {/* Submissions Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-500 uppercase font-bold border-b border-slate-200 text-[10px]">
                  <tr>
                    <th className="p-3">Paper Details</th>
                    <th className="p-3">Subject</th>
                    <th className="p-3">Author</th>
                    <th className="p-3">Scrutiny Score</th>
                    <th className="p-3">Moderator Status</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {recentPapers.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-10 text-center">
                        <div className="max-w-xs mx-auto space-y-3">
                          <div className="w-10 h-10 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
                            <FileText className="w-5 h-5" />
                          </div>
                          <p className="text-xs text-slate-500 font-medium">
                            No question papers found matching your selection.
                          </p>
                          <button
                            type="button"
                            onClick={() => navigate('/papers/upload')}
                            className="px-3 py-1.5 rounded-lg bg-adcet-red text-white text-xs font-bold hover:bg-red-700 transition-colors"
                          >
                            Upload Question Paper
                          </button>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    recentPapers.map((p) => {
                      const scoreVal = p.overall_score;
                      return (
                        <tr key={p.id} className="hover:bg-slate-50/80 transition-colors">
                          <td className="p-3">
                            <p className="font-bold text-slate-900 text-xs">{p.title}</p>
                            <p className="text-[10px] text-slate-400 mt-0.5">
                              {p.academic_year || 'Academic year not specified'} • {p.exam_type || 'Examination'}
                            </p>
                          </td>
                          <td className="p-3">
                            <span className="font-mono font-bold text-adcet-navy bg-slate-100 px-2 py-0.5 rounded text-[11px] border border-slate-200">
                              {p.subject_code}
                            </span>
                          </td>
                          <td className="p-3 text-slate-600 text-[11px]">
                            {p.uploaded_by || 'Faculty'}
                          </td>
                          <td className="p-3">
                            {scoreVal !== null && scoreVal !== undefined ? (
                              <div className="space-y-1">
                                <span className={`font-bold text-xs ${
                                  Number(scoreVal) >= 80
                                    ? 'text-emerald-700 font-bold'
                                    : Number(scoreVal) >= 60
                                    ? 'text-amber-700'
                                    : 'text-red-700'
                                }`}>
                                  {Number(scoreVal).toFixed(1)} / 100
                                </span>
                                <div className="w-16 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                                  <div
                                    className={`h-full rounded-full ${
                                      Number(scoreVal) >= 80 ? 'bg-emerald-500' : Number(scoreVal) >= 60 ? 'bg-amber-500' : 'bg-red-500'
                                    }`}
                                    style={{ width: `${Math.min(Number(scoreVal), 100)}%` }}
                                  />
                                </div>
                              </div>
                            ) : (
                              <span className="text-slate-400 text-[11px]">Pending Analysis</span>
                            )}
                          </td>
                          <td className="p-3">
                            <div className="space-y-1">
                              <Badge status={p.moderator_decision || p.status} />
                              {p.moderator_feedback ? (
                                <div>
                                  <p className="text-[10px] text-slate-500 truncate max-w-[170px]" title={p.moderator_feedback}>
                                    &ldquo;{p.moderator_feedback}&rdquo;
                                  </p>
                                  <button
                                    type="button"
                                    onClick={() => setFeedbackModalPaper(p)}
                                    className="inline-flex items-center gap-1 text-[10px] font-semibold text-adcet-navy hover:underline cursor-pointer"
                                  >
                                    <MessageSquare className="w-2.5 h-2.5" />
                                    <span>View Feedback</span>
                                  </button>
                                </div>
                              ) : (
                                <p className="text-[10px] text-slate-400 italic">No feedback</p>
                              )}
                            </div>
                          </td>
                          <td className="p-3 text-right">
                            <button
                              type="button"
                              onClick={() => navigate(`/papers/${p.id}`)}
                              className="px-2.5 py-1.5 bg-adcet-navy text-white hover:bg-slate-800 rounded-lg text-[11px] font-semibold transition-colors shadow-sm inline-flex items-center gap-1"
                            >
                              <span>View Scrutiny</span>
                              <ExternalLink className="w-3 h-3" />
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Right Column (4 cols): Bloom's Taxonomy & Guidelines */}
        <div className="lg:col-span-4 space-y-4">
          {/* Bloom's Cognitive Distribution Chart */}
          <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h2 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                <Brain className="w-4 h-4 text-adcet-navy" />
                Bloom's Taxonomy Distribution
              </h2>
              <span className="text-[10px] text-slate-400 font-medium">K1–K6</span>
            </div>

            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data?.bloom_distribution || []}>
                  <XAxis dataKey="level" tick={{ fontSize: 9, fill: '#64748b' }} interval={0} angle={-15} textAnchor="end" height={35} />
                  <YAxis tick={{ fontSize: 9, fill: '#64748b' }} />
                  <Tooltip contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '0.75rem', fontSize: '11px', color: '#0f172a' }} />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {(data?.bloom_distribution || []).map((_, idx) => (
                      <Cell key={idx} fill={BLOOM_COLORS[idx % BLOOM_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="text-[10px] text-slate-500 text-center">
              Distribution is informational unless an institutional Bloom target is configured.
            </p>
          </div>

          {/* Guidelines Card */}
          <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm space-y-3">
            <h2 className="text-xs font-bold text-slate-900 flex items-center gap-1.5 pb-2 border-b border-slate-100">
              <CheckSquare className="w-4 h-4 text-adcet-red" />
              Paper Setter Quality Checklist
            </h2>
            <ul className="space-y-2 text-[11px] text-slate-600">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                <span>Upload paper only into its matching subject workspace.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                <span>Ensure question marks sum exactly to the prescribed total (e.g. 100 or 50).</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                <span>Review coverage against the configured examination scope; unmapped units remain unassessed.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                <span>Review same-subject similarity flags manually; they do not establish plagiarism.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Add Subject Modal */}
      <AddSubjectModal
        isOpen={addSubjectOpen}
        onClose={() => setAddSubjectOpen(false)}
        onSubjectCreated={handleSubjectCreated}
      />

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
                    {feedbackModalPaper.title} • {feedbackModalPaper.subject_code || ''}
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

              {(feedbackModalPaper.moderator_decision || feedbackModalPaper.status) === 'MODIFICATION_REQUIRED' && (
                <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-amber-800 flex items-start space-x-2">
                  <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-600" />
                  <div className="text-[11px] leading-relaxed">
                    <span className="font-semibold">Next step:</span> The Chief Moderator has requested modifications to this paper. Please inspect the scrutiny findings and revise accordingly.
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-between items-center pt-2">
              <button
                type="button"
                onClick={() => {
                  const pid = feedbackModalPaper.id;
                  setFeedbackModalPaper(null);
                  navigate(`/papers/${pid}`);
                }}
                className="text-xs font-semibold text-adcet-navy hover:underline inline-flex items-center gap-1 cursor-pointer"
              >
                <span>Inspect Scrutiny Report</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </button>
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
