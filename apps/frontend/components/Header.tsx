'use client';

import React from 'react';
import { Activity, ShieldCheck, Database, Layers, Sparkles } from 'lucide-react';

interface HeaderProps {
  activeDomain?: string;
  onSelectDomain?: (domain: string) => void;
}

export function Header({ activeDomain = 'commercial', onSelectDomain }: HeaderProps) {
  const domains = [
    { id: 'commercial', label: 'Commercial & Sales' },
    { id: 'finance', label: 'Finance & P&L' },
    { id: 'supply_chain', label: 'Supply Chain & Inventory' },
  ];

  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur px-6 py-3.5 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-base text-white tracking-tight">OPELLA</span>
              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                AI Cockpit
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-normal">
              Enterprise Conversational Analytics & Decision Intelligence
            </p>
          </div>
        </div>

        {/* Domain selector tabs */}
        <div className="hidden md:flex items-center gap-1.5 ml-6 bg-slate-950/60 p-1 rounded-lg border border-slate-800">
          {domains.map((d) => (
            <button
              key={d.id}
              onClick={() => onSelectDomain?.(d.id)}
              className={`px-3 py-1 text-xs rounded-md font-medium transition-all ${
                activeDomain === d.id
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Warehouse Status */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800/80 border border-slate-700/60 text-slate-300">
          <Database size={13} className="text-indigo-400" />
          <span>Local DuckDB</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        </div>

        {/* Guardrail Status */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800/80 border border-slate-700/60 text-slate-300">
          <ShieldCheck size={13} className="text-emerald-400" />
          <span>Guardrails Active</span>
        </div>
      </div>
    </header>
  );
}
