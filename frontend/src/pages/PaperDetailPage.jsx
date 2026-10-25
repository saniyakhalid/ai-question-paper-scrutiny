import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { papersAPI, reportsAPI } from '../services/api';
import { 
  FileText, CheckCircle2, AlertTriangle, XCircle, Award, 
  HelpCircle, Eye, ShieldCheck, Download, ExternalLink 
} from 'lucide-react';

export default function PaperDetailPage() {
  const { id } = useParams();
  const [paper, setPaper] = useState(null);
  const [report, setReport] = useState(null);
  const [activeTab, setActiveTab] = useState('questions');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const pRes = await papersAPI.get(id);
        setPaper(pRes.data);
        try {
          const rRes = await reportsAPI.get(id);
          setReport(rRes.data);
        } catch (e) {
          // Report may not exist yet
        }
      } catch (err) {
        console.error("Failed to load paper details", err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [id]);

  if (loading) return <div className="p-8 text-center text-slate-500">Loading paper scrutiny details...</div>;
  if (!paper) return <div className="p-8 text-center text-red-500">Paper not found.</div>;

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <h1 className="text-xl font-bold text-slate-900">{paper.title}</h1>
            <span className="px-2.5 py-0.5 text-xs font-bold bg-blue-100 text-blue-800 rounded-full">v{paper.version}</span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Subject: <span className="font-semibold text-slate-700">{paper.subject?.code} - {paper.subject?.name}</span> | 
            Exam: <span className="font-semibold text-slate-700">{paper.exam_type} ({paper.academic_year})</span>
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="text-right">
            <div className="text-xs text-slate-400 font-medium">Scrutiny DSS Score</div>
            <div className="text-2xl font-black text-blue-600">{paper.overall_score !== null ? `${paper.overall_score}/100` : 'N/A'}</div>
          </div>
          
          {report && (
            <a
              href={reportsAPI.exportPDF(paper.id)}
              target="_blank"
              rel="noreferrer"
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-xs flex items-center gap-1.5"
            >
              <Download className="w-3.5 h-3.5" /> Export Report (PDF)
            </a>
          )}
        </div>
      </div>

      {/* Tabs Bar */}
      <div className="border-b border-slate-200 flex space-x-4">
        {[
          { id: 'questions', label: 'Structured Questions' },
          { id: 'bloom', label: "Bloom's Taxonomy" },
          { id: 'co', label: 'CO & Syllabus Mapping' },
          { id: 'grammar', label: 'Grammar & Clarity' },
          { id: 'rules', label: 'Rule Validation Engine' },
          { id: 'recommendations', label: 'AI Recommendations' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`py-2.5 px-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-blue-600 text-blue-600 font-semibold'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Structured Questions */}
      {activeTab === 'questions' && (
        <div className="space-y-4">
          {paper.questions.map((q) => (
            <div key={q.id} className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-900 bg-slate-100 px-2.5 py-1 rounded-md text-sm">{q.original_number}</span>
                <div className="flex items-center space-x-3 text-xs">
                  <span className="font-semibold text-slate-700 bg-blue-50 px-2 py-1 rounded-sm">{q.marks != null ? `${q.marks} Marks` : 'Marks not detected'}</span>
                  {q.internal_choice && <span className="bg-amber-50 text-amber-700 font-semibold px-2 py-1 rounded-sm">Internal Choice</span>}
                  <span className="text-slate-500 font-medium">{q.section}</span>
                </div>
              </div>
              <p className="text-slate-800 text-sm font-mono bg-slate-50 p-3 rounded-lg border border-slate-100">{q.question_text}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tab 2: Bloom Classification */}
      {activeTab === 'bloom' && (
        <div className="space-y-4">
          {paper.questions.map((q) => (
            <div key={q.id} className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-900 text-sm">{q.original_number}: {q.question_text}</span>
                <span className="px-3 py-1 bg-purple-100 text-purple-800 font-bold text-xs rounded-full">
                  {q.bloom_level_ai || 'Analyze'} ({(q.bloom_confidence * 100).toFixed(0)}% Conf)
                </span>
              </div>
              <div className="p-3 bg-purple-50/50 border border-purple-100 rounded-lg text-xs text-purple-900">
                <span className="font-bold">AI Cognitive Reason:</span> {q.bloom_explanation}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab 3: CO & Syllabus Mapping */}
      {activeTab === 'co' && (
        <div className="space-y-4">
          {paper.questions.map((q) => (
            <div key={q.id} className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-2">
              <div className="font-bold text-slate-900 text-sm">{q.original_number}: {q.question_text}</div>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-lg">
                  <span className="font-bold text-emerald-900">Course Outcome (CO):</span> CO{q.co_id_ai || 1}
                </div>
                <div className="p-3 bg-blue-50 border border-blue-100 rounded-lg">
                  <span className="font-bold text-blue-900">Syllabus Unit:</span> Unit {q.unit_id_ai || 1}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab 4: Grammar & Language Quality */}
      {activeTab === 'grammar' && (
        <div className="space-y-4">
          {paper.questions.map((q) => (
            <div key={q.id} className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-900 text-sm">{q.original_number}: {q.question_text}</span>
                <span className="px-2.5 py-1 bg-slate-100 text-slate-700 font-semibold text-xs rounded-md">Quality Score: {q.quality_score}/100</span>
              </div>
              {q.grammar_issues && q.grammar_issues.length > 0 ? (
                q.grammar_issues.map((issue, idx) => (
                  <div key={idx} className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs space-y-1">
                    <div className="font-bold text-amber-900">{issue.issue_type}: {issue.explanation}</div>
                    <div className="text-amber-800"><span className="font-semibold">Suggested Improvement:</span> {issue.suggested_improvement}</div>
                  </div>
                ))
              ) : (
                <div className="p-2 bg-emerald-50 text-emerald-800 text-xs font-semibold rounded-md">
                  No grammatical ambiguity or phrasing issues detected.
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Tab 5: Rule Engine Validation */}
      {activeTab === 'rules' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 border-b border-slate-200 font-semibold text-slate-600">
              <tr>
                <th className="p-3">Rule Name</th>
                <th className="p-3">Category</th>
                <th className="p-3">Expected</th>
                <th className="p-3">Actual</th>
                <th className="p-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {report?.rule_results.map((r) => (
                <tr key={r.id}>
                  <td className="p-3 font-medium text-slate-900">{r.rule_name}</td>
                  <td className="p-3 text-slate-600">{r.category}</td>
                  <td className="p-3 text-slate-600">{r.expected}</td>
                  <td className="p-3 text-slate-600">{r.actual}</td>
                  <td className="p-3">
                    {r.status === 'PASS' ? (
                      <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 text-xs font-bold rounded-full">PASS</span>
                    ) : (
                      <span className="px-2 py-0.5 bg-amber-100 text-amber-800 text-xs font-bold rounded-full">{r.status}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab 6: AI Recommendations */}
      {activeTab === 'recommendations' && (
        <div className="space-y-3">
          {report?.findings.map((f) => (
            <div key={f.id} className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs space-y-1">
              <div className="font-bold text-slate-900 text-sm">{f.category} ({f.severity})</div>
              <p className="text-xs text-slate-700">{f.finding_text}</p>
              {f.recommendation && (
                <div className="p-2 bg-blue-50 text-blue-900 rounded-md text-xs font-medium">
                  Recommendation: {f.recommendation}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
