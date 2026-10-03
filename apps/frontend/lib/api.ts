// API Client — SSE streaming chat

import type { ChatResponse, TraceNode } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api';

export interface StreamCallbacks {
  onTrace: (event: TraceNode) => void;
  onResponse: (response: ChatResponse) => void;
  onError: (error: string) => void;
  onDone: () => void;
}

export async function streamChat(
  message: string,
  conversationId: string | null,
  callbacks: StreamCallbacks,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

  if (!res.ok || !res.body) {
    callbacks.onError(`HTTP ${res.status}: ${res.statusText}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split('\n\n');
    buffer = events.pop() ?? '';

    for (const raw of events) {
      if (!raw.trim()) continue;
      const lines = raw.split('\n');
      let eventType = 'message';
      let dataStr = '';

      for (const line of lines) {
        if (line.startsWith('event: ')) eventType = line.slice(7).trim();
        if (line.startsWith('data: ')) dataStr = line.slice(6).trim();
      }

      if (!dataStr) continue;
      try {
        const payload = JSON.parse(dataStr);
        if (eventType === 'trace') callbacks.onTrace(payload as TraceNode);
        else if (eventType === 'response') callbacks.onResponse(payload as ChatResponse);
        else if (eventType === 'error') callbacks.onError(payload.message);
        else if (eventType === 'done') callbacks.onDone();
      } catch {
        // ignore parse errors
      }
    }
  }

  callbacks.onDone();
}
