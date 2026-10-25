import React from 'react';

export default function ScoreCard({ title, value, subtitle, icon: Icon, color = 'brand', badge }) {
  const colorStyles = {
    brand: 'text-brand-700 dark:text-indigo-400 bg-brand-600/10 border-brand-600/20',
    emerald: 'text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    amber: 'text-amber-700 dark:text-amber-400 bg-amber-500/10 border-amber-500/20',
    rose: 'text-rose-700 dark:text-rose-400 bg-rose-500/10 border-rose-500/20',
    blue: 'text-blue-700 dark:text-blue-400 bg-blue-500/10 border-blue-500/20',
  };

  return (
    <div className="bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl relative overflow-hidden transition-all hover:shadow-md hover:border-slate-300 dark:hover:border-slate-700">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">{title}</span>
        {Icon && (
          <div className={`p-2 rounded-xl border ${colorStyles[color] || colorStyles.brand}`}>
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      <div className="mt-3 flex items-baseline space-x-2">
        <p className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">{value}</p>
        {badge && (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
            {badge}
          </span>
        )}
      </div>

      {subtitle && (
        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 truncate">{subtitle}</p>
      )}
    </div>
  );
}
