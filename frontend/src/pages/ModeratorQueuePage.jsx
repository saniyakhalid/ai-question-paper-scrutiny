import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import Badge from '../components/common/Badge';
import { AlertCircle, CheckCircle2, ExternalLink, FileText, Loader2 } from 'lucide-react';

const ANALYSIS_STATUSES = new Set(['SUBMITTED', 'EXTRACTED', 'ANALYZING']);
const READY_STATUSES = new Set(['PENDING_REVIEW']);
const FAILED_STATUSES = new Set(['FAILED', 'EXTRACTION_FAILED']);

function PapersTable({ papers }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] text-left text-sm">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-5 py-3">Question paper</th>
            <th className="px-5 py-3">Subject</th>
            <th className="px-5 py-3">Exam</th>
            <th className="px-5 py-3">Scrutiny score</th>
            <th className="px-5 py-3">Status</th>
            <th className="px-5 py-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {papers.map((paper) => (
            <tr key={paper.id} className="align-top hover:bg-slate-50/70">
              <td className="px-5 py-4">
                <p className="font-semibold text-slate-900">{paper.title || `Paper #${paper.id}`}</p>
                <p className="mt-0.5 text-xs text-slate-500">Academic year {paper.academic_year || '—'}</p>
              </td>
              <td className="px-5 py-4 text-slate-600">{paper.subject?.code || '—'}{paper.subject?.name ? ` · ${paper.subject.name}` : ''}</td>
              <td className="px-5 py-4 text-slate-600">{paper.exam_type || '—'}</td>
              <td className="px-5 py-4 font-semibold text-slate-800">{paper.overall_score == null ? '—' : `${paper.overall_score}%`}</td>
              <td className="px-5 py-4"><Badge status={paper.status} /></td>
              <td className="px-5 py-4 text-right">
                <Link to={`/papers/${paper.id}`} className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-semibold text-white bg-adcet-navy hover:bg-slate-800">
                  Inspect paper <ExternalLink className="h-3.5 w-3.5" />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ModeratorQueuePage() {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    api.get('/papers')
      .then(({ data }) => {
        if (active) setPapers(data || []);
      })
      .catch((err) => {
        if (active) setError(err.response?.data?.detail || 'Could not load the review queue. Please try again.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  const readyPapers = papers.filter((paper) => READY_STATUSES.has(paper.status) && paper.validation_status === 'VALID_MATCH');
  const awaitingAnalysisPapers = papers.filter((paper) => ANALYSIS_STATUSES.has(paper.status) && paper.validation_status === 'VALID_MATCH');
  const failedAnalysisPapers = papers.filter((paper) => FAILED_STATUSES.has(paper.status) && paper.validation_status === 'VALID_MATCH');

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <header className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-adcet-red">Moderator workspace</p>
          <h1 className="mt-1 text-2xl font-bold text-adcet-navy">Paper review queue</h1>
          <p className="mt-1 text-sm text-slate-500">Open a submission to inspect its scrutiny results and record the official decision.</p>
        </div>
        <span className="inline-flex w-fit items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-800">
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileText className="h-3.5 w-3.5" />}
          {loading ? 'Loading queue' : `${readyPapers.length} ready · ${awaitingAnalysisPapers.length} awaiting analysis`}
        </span>
      </header>

      {error && (
        <div role="alert" className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}
        </div>
      )}

      {(loading || error || (!loading && !error && readyPapers.length === 0 && awaitingAnalysisPapers.length === 0 && failedAnalysisPapers.length === 0)) && (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="p-10 text-center text-sm text-slate-500">Loading submitted papers…</div>
        ) : error ? null : readyPapers.length === 0 && awaitingAnalysisPapers.length === 0 && failedAnalysisPapers.length === 0 ? (
          <div className="p-12 text-center">
            <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-500" />
            <h2 className="mt-3 font-semibold text-slate-900">The review queue is clear</h2>
            <p className="mt-1 text-sm text-slate-500">New submissions will appear here after they are uploaded.</p>
          </div>
        ) : null}
        </section>
      )}

      {!loading && !error && readyPapers.length > 0 && (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900">Ready for moderator decision</h2>
            <p className="mt-1 text-xs text-slate-500">These papers passed subject validation and completed their scrutiny report.</p>
          </div>
          <PapersTable papers={readyPapers} />
        </section>
      )}

      {!loading && !error && awaitingAnalysisPapers.length > 0 && (
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 p-5">
            <h2 className="font-semibold text-slate-900">Validated submissions awaiting analysis</h2>
            <p className="mt-1 text-xs text-slate-500">These passed subject validation but do not have a final scrutiny report yet.</p>
          </div>
          <PapersTable papers={awaitingAnalysisPapers} />
        </section>
      )}

      {!loading && !error && failedAnalysisPapers.length > 0 && (
        <section className="overflow-hidden rounded-2xl border border-rose-200 bg-white shadow-sm">
          <div className="border-b border-rose-100 bg-rose-50 p-5">
            <h2 className="font-semibold text-rose-950">Analysis issues ({failedAnalysisPapers.length})</h2>
            <p className="mt-1 text-xs text-rose-900">Inspect the paper record to see whether extraction or scrutiny can be retried.</p>
          </div>
          <PapersTable papers={failedAnalysisPapers} />
        </section>
      )}
    </div>
  );
}
