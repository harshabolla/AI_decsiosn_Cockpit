'use client';

import React, { useState, KeyboardEvent } from 'react';
import { Send, Mic, Sparkles, StopCircle } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  isStreaming: boolean;
  onStop?: () => void;
}

const SUGGESTIONS = [
  'Show sales by product line for 2024',
  'What is the inventory level of Doliprane?',
  'Top 5 margin brands across Europe',
  'Compare commercial performance Q2 vs Q3',
];

export function ChatInput({ onSend, isStreaming, onStop }: ChatInputProps) {
  const [input, setInput] = useState('');

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;
    onSend(trimmed);
    setInput('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="w-full space-y-3">
      {/* Prompt Suggestions */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar text-xs">
        <span className="text-slate-500 flex items-center gap-1 shrink-0 text-[11px] font-medium uppercase tracking-wider">
          <Sparkles size={12} className="text-indigo-400" /> Prompts:
        </span>
        {SUGGESTIONS.map((s, idx) => (
          <button
            key={idx}
            disabled={isStreaming}
            onClick={() => onSend(s)}
            className="px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-indigo-500/50 hover:bg-slate-800/80 transition-all text-xs shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {s}
          </button>
        ))}
      </div>

      {/* Input Box */}
      <div className="relative rounded-2xl border border-slate-800 bg-slate-900/90 shadow-2xl p-2.5 focus-within:border-indigo-500/70 focus-within:ring-1 focus-within:ring-indigo-500/50 transition-all">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a commercial, finance, or supply chain question... (e.g., 'Show sales by product')"
          rows={2}
          className="w-full bg-transparent resize-none outline-none text-sm text-slate-100 placeholder-slate-500 px-2 py-1 leading-relaxed"
        />

        <div className="flex items-center justify-between pt-1 border-t border-slate-800/80 px-1">
          <div className="flex items-center gap-2 text-[11px] text-slate-500">
            <span>Press <kbd className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">Enter ↵</kbd> to submit</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              title="Voice Input (Multimodal)"
              className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
            >
              <Mic size={17} />
            </button>

            {isStreaming ? (
              <button
                type="button"
                onClick={onStop}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium transition-all shadow-md shadow-rose-600/20"
              >
                <StopCircle size={15} />
                <span>Stop</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSend}
                disabled={!input.trim()}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white text-xs font-medium transition-all shadow-md shadow-indigo-600/20"
              >
                <Send size={14} />
                <span>Send</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
