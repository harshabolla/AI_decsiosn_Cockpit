'use client';

import React, { useState } from 'react';
import { Code2, CheckCircle, AlertTriangle, XCircle, ChevronDown, ChevronUp, Copy, Check } from 'lucide-react';
import type { SQLResult } from '@/types';

interface SQLPanelProps {
  sql: SQLResult;
}

function StatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'valid':
      return (
        <span className="flex items-center gap-1 text-xs text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full">
          <CheckCircle size={10} /> Valid
        </span>
      );
    case 'warning':
      return (
        <span className="flex items-center gap-1 text-xs text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded-full">
          <AlertTriangle size={10} /> Warning
        </span>
      );
    case 'invalid':
      return (
        <span className="flex items-center gap-1 text-xs text-red-400 bg-red-400/10 px-2 py-0.5 rounded-full">
          <XCircle size={10} /> Invalid
        </span>
      );
    default:
      return null;
  }
}

export function SQLPanel({ sql }: SQLPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(sql.sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-900/60 overflow-hidden">
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-800/40 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Code2 size={14} className="text-indigo-400" />
          <span className="text-xs font-medium text-slate-300">SQL Query</span>
          <StatusBadge status={sql.validation_status} />
        </div>
        <div className="flex items-center gap-3">
          {sql.rows_returned != null && (
            <span className="text-[10px] text-slate-500">{sql.rows_returned} rows</span>
          )}
          {sql.execution_time_ms != null && (
            <span className="text-[10px] text-slate-500">{Math.round(sql.execution_time_ms)}ms</span>
          )}
          {expanded ? <ChevronUp size={14} className="text-slate-500" /> : <ChevronDown size={14} className="text-slate-500" />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-slate-700/50">
          <div className="relative">
            <pre className="p-4 text-xs text-slate-300 font-mono overflow-auto max-h-48 bg-slate-950/80 leading-relaxed">
              {sql.sql}
            </pre>
            <button
              onClick={handleCopy}
              className="absolute top-2 right-2 p-1.5 rounded-md hover:bg-slate-700 transition-colors"
              title="Copy SQL"
            >
              {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} className="text-slate-400" />}
            </button>
          </div>

          <div className="px-4 py-3 grid grid-cols-2 gap-3 border-t border-slate-800/60">
            {sql.tables.length > 0 && (
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Tables</p>
                <div className="flex flex-wrap gap-1">
                  {sql.tables.map(t => (
                    <span key={t} className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {sql.assumptions.length > 0 && (
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Assumptions</p>
                <ul className="space-y-0.5">
                  {sql.assumptions.map((a, i) => (
                    <li key={i} className="text-[10px] text-slate-400">{a}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
