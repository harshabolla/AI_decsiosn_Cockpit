'use client';

import React from 'react';
import { Database, FileText, AlertCircle, BookOpen } from 'lucide-react';
import type { EvidenceItem } from '@/types';

interface EvidencePanelProps {
  sources: EvidenceItem[];
  adapterNote?: string | null;
}

const SOURCE_ICONS: Record<string, React.ReactNode> = {
  snowflake: <Database size={12} className="text-blue-400" />,
  rag: <FileText size={12} className="text-purple-400" />,
  servicenow: <AlertCircle size={12} className="text-orange-400" />,
  guideline: <BookOpen size={12} className="text-emerald-400" />,
  semantic: <BookOpen size={12} className="text-indigo-400" />,
};

export function EvidencePanel({ sources, adapterNote }: EvidencePanelProps) {
  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
        Evidence Sources
      </h3>

      {adapterNote && (
        <div className="text-[10px] bg-amber-500/10 border border-amber-500/30 text-amber-400 px-3 py-2 rounded-lg">
          {adapterNote}
        </div>
      )}

      {sources.length === 0 ? (
        <p className="text-xs text-slate-600">No sources available.</p>
      ) : (
        <div className="space-y-2">
          {sources.map((s, i) => (
            <div key={i} className="rounded-lg border border-slate-700/40 bg-slate-900/40 px-3 py-2.5">
              <div className="flex items-center gap-1.5 mb-1">
                {SOURCE_ICONS[s.source_type] ?? <Database size={12} />}
                <span className="text-[10px] font-medium text-slate-300">{s.source_name}</span>
                <span className="text-[9px] text-slate-600 bg-slate-800 px-1.5 py-0.5 rounded-full ml-auto capitalize">
                  {s.source_type}
                </span>
              </div>
              <p className="text-[11px] text-slate-400">{s.summary}</p>
              {s.citation && (
                <p className="text-[10px] text-slate-600 mt-1 italic">{s.citation}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
