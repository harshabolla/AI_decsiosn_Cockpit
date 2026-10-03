'use client';

import React from 'react';
import { CheckCircle, XCircle, Loader2, Clock, SkipForward } from 'lucide-react';
import type { TraceNode, NodeStatus } from '@/types';

interface ExecutionTraceProps {
  nodes: TraceNode[];
}

const NODE_LABELS: Record<string, string> = {
  security: 'Security Gateway',
  intent: 'Intent Detection',
  semantic: 'Semantic Resolver',
  analytics: 'Analytics Agent',
  visualization: 'Visualization Agent',
  summary: 'Response Generator',
  rag: 'Knowledge RAG',
  guideline: 'Guideline Engine',
  reviewer: 'Reviewer Agent',
  guardrail: 'Output Guardrail',
};

const NODE_ORDER = [
  'security', 'intent', 'semantic', 'analytics',
  'rag', 'guideline', 'visualization', 'reviewer', 'guardrail', 'summary',
];

function StatusIcon({ status }: { status: NodeStatus }) {
  switch (status) {
    case 'running':
      return <Loader2 size={14} className="animate-spin text-indigo-400" />;
    case 'success':
      return <CheckCircle size={14} className="text-emerald-400" />;
    case 'failed':
      return <XCircle size={14} className="text-red-400" />;
    case 'skipped':
      return <SkipForward size={14} className="text-slate-500" />;
    default:
      return <Clock size={14} className="text-slate-600" />;
  }
}

function statusBg(status: NodeStatus): string {
  switch (status) {
    case 'running': return 'border-indigo-500/60 bg-indigo-500/10';
    case 'success': return 'border-emerald-500/40 bg-emerald-500/8';
    case 'failed':  return 'border-red-500/40 bg-red-500/8';
    case 'skipped': return 'border-slate-600/30 bg-slate-800/20';
    default:        return 'border-slate-700/30 bg-slate-800/10';
  }
}

export function ExecutionTrace({ nodes }: ExecutionTraceProps) {
  const nodeMap = new Map(nodes.map(n => [n.node, n]));

  const orderedNodes = NODE_ORDER
    .map(key => ({ key, node: nodeMap.get(key) ?? null }))
    .filter(({ node }) => node !== null || nodes.length === 0);

  const displayNodes: TraceNode[] = nodes.length > 0
    ? nodes
    : NODE_ORDER.map(key => ({
        node: key, status: 'waiting' as NodeStatus,
        timestamp: '', duration_ms: null, summary: '', error: null,
      }));

  return (
    <div className="space-y-1.5">
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
        AI Execution Pipeline
      </h3>
      {displayNodes.map((n, i) => {
        const label = NODE_LABELS[n.node] ?? n.node;
        const status = n.status as NodeStatus;
        return (
          <div key={n.node} className={`relative flex items-start gap-3 rounded-lg border px-3 py-2 transition-all duration-300 ${statusBg(status)}`}>
            {/* Connector line */}
            {i < displayNodes.length - 1 && (
              <div className="absolute left-[1.35rem] top-full w-px h-1.5 bg-slate-700 z-0" />
            )}
            <div className="mt-0.5 shrink-0 z-10">
              <StatusIcon status={status} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <span className={`text-xs font-medium ${status === 'running' ? 'text-indigo-300' : status === 'success' ? 'text-slate-200' : status === 'failed' ? 'text-red-300' : 'text-slate-500'}`}>
                  {label}
                </span>
                {n.duration_ms != null && (
                  <span className="text-[10px] text-slate-500 shrink-0">
                    {n.duration_ms < 1000 ? `${Math.round(n.duration_ms)}ms` : `${(n.duration_ms / 1000).toFixed(1)}s`}
                  </span>
                )}
              </div>
              {n.summary && status !== 'waiting' && (
                <p className="text-[10px] text-slate-500 mt-0.5 truncate">{n.summary}</p>
              )}
              {n.error && (
                <p className="text-[10px] text-red-400 mt-0.5 truncate">{n.error}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
