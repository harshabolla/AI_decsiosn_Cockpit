'use client';

import { useCallback, useRef, useState } from 'react';
import { streamChat } from '@/lib/api';
import type { ChatResponse, Message, TraceNode } from '@/types';

export function useChat(conversationId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [traceNodes, setTraceNodes] = useState<TraceNode[]>([]);
  const [currentResponse, setCurrentResponse] = useState<ChatResponse | null>(null);
  const abortRef = useRef<(() => void) | null>(null);

  const sendMessage = useCallback(async (content: string) => {
    if (isStreaming) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    const assistantMsg: Message = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    };

    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);
    setTraceNodes([]);
    setCurrentResponse(null);

    let cancelled = false;
    abortRef.current = () => { cancelled = true; };

    try {
      await streamChat(content, conversationId, {
        onTrace: (event) => {
          if (cancelled) return;
          setTraceNodes(prev => {
            const idx = prev.findIndex(n => n.node === event.node);
            if (idx >= 0) {
              const next = [...prev];
              next[idx] = event;
              return next;
            }
            return [...prev, event];
          });
        },
        onResponse: (response) => {
          if (cancelled) return;
          setCurrentResponse(response);
          setMessages(prev =>
            prev.map(m =>
              m.id === assistantMsg.id
                ? { ...m, content: response.answer, response, isStreaming: false }
                : m,
            ),
          );
        },
        onError: (error) => {
          if (cancelled) return;
          setMessages(prev =>
            prev.map(m =>
              m.id === assistantMsg.id
                ? { ...m, content: `Error: ${error}`, isStreaming: false }
                : m,
            ),
          );
        },
        onDone: () => {
          if (cancelled) return;
          setIsStreaming(false);
          setMessages(prev =>
            prev.map(m => m.id === assistantMsg.id ? { ...m, isStreaming: false } : m),
          );
        },
      });
    } catch (e) {
      setIsStreaming(false);
    }
  }, [isStreaming, conversationId]);

  const stopStreaming = useCallback(() => {
    abortRef.current?.();
    setIsStreaming(false);
  }, []);

  return { messages, isStreaming, traceNodes, currentResponse, sendMessage, stopStreaming };
}
