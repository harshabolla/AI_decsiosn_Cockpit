// Opella AI Decision Cockpit — Shared TypeScript Types

export type NodeStatus = 'waiting' | 'running' | 'success' | 'failed' | 'skipped';

export interface TraceNode {
  node: string;
  status: NodeStatus;
  timestamp: string;
  duration_ms: number | null;
  summary: string;
  error?: string | null;
}

export interface KPI {
  label: string;
  value: string;
  trend: number | null;
  trend_direction: 'up' | 'down' | 'neutral' | null;
  unit: string;
}

export interface VisualizationSpec {
  type: 'bar' | 'line' | 'area' | 'donut' | 'scatter' | 'table' | 'kpi';
  title: string;
  x?: string | null;
  y?: string | null;
  data: Record<string, unknown>[];
  config: Record<string, unknown>;
  columns?: string[];
}

export interface SQLResult {
  sql: string;
  tables: string[];
  columns: string[];
  filters: string[];
  assumptions: string[];
  execution_time_ms: number | null;
  rows_returned: number | null;
  validation_status: 'valid' | 'invalid' | 'warning' | 'unknown';
}

export interface EvidenceItem {
  source_type: 'snowflake' | 'rag' | 'servicenow' | 'semantic' | 'guideline';
  source_name: string;
  summary: string;
  timestamp: string | null;
  citation: string | null;
}

export interface Confidence {
  overall: number;
  data_confidence: number;
  reasoning_confidence: number;
  label: 'low' | 'medium' | 'high';
}

export type ActionStatus = 'proposed' | 'pending_approval' | 'approved' | 'rejected' | 'executed';

export interface ProposedAction {
  action_id: string;
  action_type: string;
  title: string;
  description: string;
  status: ActionStatus;
  payload: Record<string, unknown>;
}

export interface ChatResponse {
  trace_id: string;
  answer: string;
  kpis: KPI[];
  visualizations: VisualizationSpec[];
  sources: EvidenceItem[];
  sql: SQLResult | null;
  guidelines: Record<string, unknown>[];
  actions: ProposedAction[];
  confidence: Confidence;
  execution_trace: TraceNode[];
  warnings: string[];
  adapter_note: string | null;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  response?: ChatResponse;
  isStreaming?: boolean;
}
