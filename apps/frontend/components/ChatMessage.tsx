'use client';

import React from 'react';
import { User, Bot, AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';
import type { Message } from '@/types';
import { KPISection } from './KPISection';
import { ChartPanel } from './ChartPanel';
import { SQLPanel } from './SQLPanel';
import { EvidencePanel } from './EvidencePanel';

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const response = message.response;

  return (
    <div className={`flex gap-3.5 ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      {/* Assistant Avatar */}
      {!isUser && (
        <div className="h-8 w-8 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center shrink-0 mt-0.5 text-indigo-400">
          <Bot size={17} />
        </div>
      )}

      {/* Bubble Container */}
      <div className={`max-w-[85%] md:max-w-[78%] space-y-3`}>
        <div
          className={`p-4 rounded-2xl ${
            isUser
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/10 rounded-tr-sm ml-auto'
              : 'bg-slate-900/90 border border-slate-800 text-slate-100 rounded-tl-sm shadow-xl'
          }`}
        >
          {/* User message simple text */}
          {isUser && <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>}

          {/* Assistant rich response */}
          {!isUser && (
            <div className="space-y-4">
              {/* Header with confidence & warnings if available */}
              {response?.confidence && (
                <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-xs">
                  <div className="flex items-center gap-1.5">
                    <span className="text-slate-400 font-medium">Confidence:</span>
                    <span
                      className={`px-2 py-0.5 rounded-full font-semibold uppercase text-[10px] ${
                        response.confidence.label === 'high'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : response.confidence.label === 'medium'
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}
                    >
                      {response.confidence.label} ({Math.round(response.confidence.overall * 100)}%)
                    </span>
                  </div>

                  {response.adapter_note && (
                    <div className="flex items-center gap-1 text-[11px] text-amber-400/90 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full">
                      <AlertTriangle size={11} />
                      <span>{response.adapter_note}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Streaming loading skeleton or text */}
              {message.isStreaming && !message.content ? (
                <div className="flex items-center gap-2 text-slate-400 text-sm py-2">
                  <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping" />
                  <span>Synthesizing response through multi-agent pipeline...</span>
                </div>
              ) : (
                <div className="text-sm leading-relaxed prose prose-invert max-w-none text-slate-200">
                  {message.content}
                </div>
              )}

              {/* KPIs Section */}
              {response?.kpis && response.kpis.length > 0 && (
                <KPISection kpis={response.kpis} />
              )}

              {/* Visualizations (Charts) */}
              {response?.visualizations && response.visualizations.length > 0 && (
                <div className="space-y-4 my-3">
                  {response.visualizations.map((spec, i) => (
                    <div key={i} className="p-3 bg-slate-950/60 rounded-xl border border-slate-800">
                      <ChartPanel spec={spec} />
                    </div>
                  ))}
                </div>
              )}

              {/* Generated SQL Panel */}
              {response?.sql && (
                <div className="mt-3">
                  <SQLPanel sql={response.sql} />
                </div>
              )}

              {/* Evidence & Sources */}
              {response?.sources && response.sources.length > 0 && (
                <div className="mt-3">
                  <EvidencePanel sources={response.sources} adapterNote={response.adapter_note} />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="h-8 w-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 mt-0.5 text-slate-300">
          <User size={16} />
        </div>
      )}
    </div>
  );
}
