import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { reportsAPI, papersAPI } from '../services/api';
import { FileText, Download, CheckCircle2, AlertTriangle, XCircle, Award } from 'lucide-react';

export default function ScrutinyReportPage() {
  const { id } = useParams();
  const [report, setReport] = useState(null);
  const [paper, setPaper] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadReport = async () => {
      try {
        const rRes = await reportsAPI.get(id);
        setReport(rRes.data);
        const pRes = await papersAPI.get(id);
        setPaper(pRes.data);
      } catch (err) {
        console.error("Failed to load report", err);
      } finally {
        setLoading(false);
      }
    };
    loadReport();
  }, [id]);

  if (loading) return <div className="p-8 text-center text-slate-500">Loading Official Scrutiny Report...</div>;
  if (!report) return <div className="p-8 text-center text-red-500">Scrutiny Report not found.</div>;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm space-y-6">
        <div className="flex items-center justify-between border-b border-slate-200 pb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">OFFICIAL QUESTION PAPER SCRUTINY REPORT</h1>
            <p className="text-xs text-slate-500 mt-1">Autonomous Engineering Colleges Examination Decision Support System</p>
          </div>
          <a
            href={reportsAPI.exportPDF(id)}
            target="_blank"
            rel="noreferrer"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-lg shadow-xs flex items-center gap-2"
          >
            <Download className="w-4 h-4" /> Download PDF Report
          </a>
        </div>

        {/* Paper Meta */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-slate-50 rounded-lg text-xs border border-slate-200">
          <div><span className="font-semibold text-slate-500 block">Paper Title</span><span className="font-bold text-slate-900">{paper?.title}</span></div>
          <div><span className="font-semibold text-slate-500 block">Subject Code</span><span className="font-bold text-slate-900">{paper?.subject?.code}</span></div>
          <div><span className="font-semibold text-slate-500 block">{report.evidence_coverage_pct != null && report.evidence_coverage_pct < 100 ? 'Partial DSS Score' : 'Overall DSS Score'}</span><span className="font-extrabold text-blue-600 text-base">{report.overall_score == null ? 'Unavailable' : `${Number(report.overall_score).toFixed(1)}/100`}</span>{report.evidence_coverage_pct != null && report.evidence_coverage_pct < 100 && <span className="block text-amber-700">{report.evidence_coverage_pct}% of scoring checks evaluated</span>}</div>
          <div><span className="font-semibold text-slate-500 block">Compliance Status</span><span className="font-bold text-emerald-700">{report.compliance_status}</span></div>
        </div>

        {report.analysis_notice && (
          <div className="p-4 bg-sky-50 border border-sky-200 rounded-lg text-xs text-sky-900">
            <strong>Analysis method:</strong> {report.analysis_notice}
          </div>
        )}

        {report.score_breakdown?.categories && (
          <section className="space-y-3">
            <h2 className="font-bold text-slate-900">Scoring evidence</h2>
            <p className="text-xs text-slate-600">The displayed score is normalized over evaluated checks. Unavailable checks receive no points and are excluded from the evaluated-weight denominator; the evidence coverage above shows how much of the 100-point rubric was assessed.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.entries(report.score_breakdown.categories).map(([key, category]) => (
                <div key={key} className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <div className="text-xs font-semibold text-slate-700 capitalize">{key.replaceAll('_', ' ')}</div>
                  <div className="mt-1 font-bold text-slate-900">{category.score == null ? 'Not evaluated' : `${category.score} / ${category.max}`}</div>
                  <div className="text-[10px] text-slate-500">{category.status?.replaceAll('_', ' ')}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Rule Results Table */}
        <div className="space-y-3">
          <h3 className="font-bold text-slate-900 text-sm">Deterministic Rule Engine Results</h3>
          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-100 font-semibold text-slate-700 border-b border-slate-200">
                <tr>
                  <th className="p-3">Rule Name</th>
                  <th className="p-3">Expected</th>
                  <th className="p-3">Actual</th>
                  <th className="p-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {report.rule_results.map((r) => (
                  <tr key={r.id}>
                    <td className="p-3 font-medium text-slate-900">{r.rule_name}</td>
                    <td className="p-3 text-slate-600">{r.expected || r.expected_value || '—'}</td>
                    <td className="p-3 text-slate-600">{r.actual || r.actual_value || '—'}</td>
                    <td className={`p-3 font-bold ${r.status === 'PASS' ? 'text-emerald-700' : r.status === 'NOT_EVALUATED' ? 'text-slate-500' : 'text-amber-700'}`}>{r.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* AI Recommendations */}
        <div className="space-y-3">
          <h3 className="font-bold text-slate-900 text-sm">Explainable Decision Support Findings</h3>
          {report.findings.map((f) => (
            <div key={f.id} className="p-3 bg-amber-50/60 border border-amber-200 rounded-lg text-xs space-y-1">
              <div className="font-bold text-amber-900">{f.finding_text}</div>
              <p className="text-amber-800"><span className="font-semibold">Evidence:</span> {f.evidence}</p>
              {f.recommendation && <p className="text-blue-900 font-medium"><span className="font-semibold">Recommendation:</span> {f.recommendation}</p>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
