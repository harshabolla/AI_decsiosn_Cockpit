'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Header } from '@/components/Header';
import { ChatMessage } from '@/components/ChatMessage';
import { ChatInput } from '@/components/ChatInput';
import { ExecutionTrace } from '@/components/ExecutionTrace';
import { useChat } from '@/hooks/useChat';
import { Sparkles, BarChart2, ShieldCheck, Database, Layers } from 'lucide-react';

export default function CockpitPage() {
  const [conversationId, setConversationId] = useState<string>('');
  const [activeDomain, setActiveDomain] = useState<string>('commercial');
  const chatBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setConversationId(crypto.randomUUID());
  }, []);

  const {
    messages,
    isStreaming,
    traceNodes,
    sendMessage,
    stopStreaming,
  } = useChat(conversationId);

  // Auto scroll to bottom when messages update
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, traceNodes]);

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Top Navigation */}
      <Header activeDomain={activeDomain} onSelectDomain={setActiveDomain} />

      {/* Main Workspace Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chat & Analytics Panel (Center) */}
        <main className="flex-1 flex flex-col h-full overflow-hidden bg-gradient-to-b from-slate-950 via-slate-900/40 to-slate-950">
          {/* Scrollable Conversation Stream */}
          <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 space-y-6">
            {messages.length === 0 ? (
              /* Welcome Hero / Empty State */
              <div className="h-full flex flex-col items-center justify-center max-w-2xl mx-auto text-center space-y-6 py-12 animate-fade-in">
                <div className="p-4 rounded-3xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shadow-2xl shadow-indigo-500/10">
                  <BarChart2 className="w-10 h-10" />
                </div>

                <div className="space-y-2">
                  <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                    Opella Decision Intelligence Cockpit
                  </h1>
                  <p className="text-sm text-slate-400 max-w-lg mx-auto leading-relaxed">
                    Multimodal AI & Data Platform answering governed enterprise commercial, finance, and supply chain queries using automated SQL execution, RAG, and multi-agent coordination.
                  </p>
                </div>

                {/* System Capabilities Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full text-left pt-4">
                  <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur">
                    <Database className="w-4 h-4 text-indigo-400 mb-2" />
                    <h3 className="text-xs font-semibold text-slate-200">Governed SQL Agent</h3>
                    <p className="text-[11px] text-slate-400 mt-1">
                      Validated Text-to-SQL against DuckDB / Snowflake warehouse with column validation.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur">
                    <ShieldCheck className="w-4 h-4 text-emerald-400 mb-2" />
                    <h3 className="text-xs font-semibold text-slate-200">Security & Privacy</h3>
                    <p className="text-[11px] text-slate-400 mt-1">
                      Automated PII masking, prompt-injection defense, and compliance guardrails.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur">
                    <Layers className="w-4 h-4 text-purple-400 mb-2" />
                    <h3 className="text-xs font-semibold text-slate-200">Execution Trace</h3>
                    <p className="text-[11px] text-slate-400 mt-1">
                      Full transparency into multi-agent LangGraph execution graph and evidence.
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              /* Message List */
              <>
                {messages.map((msg) => (
                  <ChatMessage key={msg.id} message={msg} />
                ))}
                <div ref={chatBottomRef} />
              </>
            )}
          </div>

          {/* Bottom Chat Input Fixed Area */}
          <div className="p-4 sm:px-8 border-t border-slate-800/80 bg-slate-950/80 backdrop-blur">
            <div className="max-w-4xl mx-auto">
              <ChatInput
                onSend={sendMessage}
                isStreaming={isStreaming}
                onStop={stopStreaming}
              />
            </div>
          </div>
        </main>

        {/* Right Sidebar: Multi-Agent Execution Trace */}
        <aside className="w-80 lg:w-96 border-l border-slate-800 bg-slate-900/50 backdrop-blur p-4 overflow-y-auto hidden md:block">
          <ExecutionTrace nodes={traceNodes} />
        </aside>
      </div>
    </div>
  );
}
