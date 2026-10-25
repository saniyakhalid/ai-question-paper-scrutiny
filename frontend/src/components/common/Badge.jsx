import React from 'react';

export default function Badge({ status, variant, children, className = '' }) {
  let text = children || status || '';
  const s = String(status || children || '').toUpperCase();

  if (!children && typeof text === 'string') {
    if (s === 'MODIFICATION_REQUIRED') text = 'CHANGES REQUIRED';
    else if (s === 'REVIEW_DECLINED') text = 'REVIEW DECLINED';
  }

  let style = 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700';

  if (s.includes('NOT_EVALUATED') || s.includes('INCONCLUSIVE')) {
    style = 'bg-slate-100 text-slate-600 border-slate-200';
  } else if (s.includes('DECLIN')) {
    style = 'bg-slate-600/10 text-slate-700 dark:text-slate-300 border-slate-600/30 font-mono';
  } else if (s.includes('MISMATCH') || s.includes('PROCESSING_FAILED')) {
    style = 'bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/30';
  } else if (variant === 'success' || s.includes('PASS') || s.includes('APPROV') || s === 'VALID_MATCH') {
    style = 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30';
  } else if (variant === 'warning' || s.includes('WARN') || s.includes('MODIFY') || s.includes('MODIF') || s.includes('CHANGE') || s.includes('REVISE') || s.includes('UNSELECTED') || s.includes('PENDING')) {
    style = 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30';
  } else if (variant === 'danger' || s.includes('FAIL') || s.includes('REJECT') || s.includes('ERROR')) {
    style = 'bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/30';
  } else if (variant === 'info' || s.includes('ANALYZ') || s.includes('EXTRACT') || s.includes('SUBMIT')) {
    style = 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border-indigo-500/30';
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${style} ${className}`}>
      {text}
    </span>
  );
}
