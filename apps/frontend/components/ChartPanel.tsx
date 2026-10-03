'use client';

import React from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { VisualizationSpec } from '@/types';

interface ChartPanelProps {
  spec: VisualizationSpec;
}

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe'];

function formatValue(val: unknown): string {
  if (typeof val === 'number') {
    if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
    if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`;
    return String(val);
  }
  return String(val ?? '');
}

export function ChartPanel({ spec }: ChartPanelProps) {
  const { type, title, x, y, data, columns } = spec;

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-slate-500 text-sm">
        No data to display
      </div>
    );
  }

  if (type === 'table') {
    const cols = columns ?? (data[0] ? Object.keys(data[0]) : []);
    return (
      <div>
        <h4 className="text-sm font-medium text-slate-300 mb-3">{title}</h4>
        <div className="overflow-auto max-h-64 rounded-lg border border-slate-700/50">
          <table className="w-full text-xs">
            <thead className="bg-slate-800/80 sticky top-0">
              <tr>
                {cols.map(c => (
                  <th key={c} className="px-3 py-2 text-left text-slate-400 font-medium capitalize">
                    {c.replace(/_/g, ' ')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, i) => (
                <tr key={i} className="border-t border-slate-800/60 hover:bg-slate-800/40 transition-colors">
                  {cols.map(c => (
                    <td key={c} className="px-3 py-2 text-slate-300">
                      {formatValue(row[c])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  const xKey = x ?? (data[0] ? Object.keys(data[0])[0] : 'x');
  const yKey = y ?? (data[0] ? Object.keys(data[0])[1] : 'y');

  if (type === 'line') {
    return (
      <div>
        <h4 className="text-sm font-medium text-slate-300 mb-3">{title}</h4>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: '#94a3b8' }} />
            <YAxis tickFormatter={v => formatValue(v)} tick={{ fontSize: 11, fill: '#94a3b8' }} width={56} />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: '#e2e8f0' }}
              formatter={(v: unknown) => [formatValue(v), yKey.replace(/_/g, ' ')]}
            />
            <Line type="monotone" dataKey={yKey} stroke="#6366f1" strokeWidth={2} dot={{ fill: '#6366f1', r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // Default: bar
  return (
    <div>
      <h4 className="text-sm font-medium text-slate-300 mb-3">{title}</h4>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey={xKey} tick={{ fontSize: 11, fill: '#94a3b8' }} />
          <YAxis tickFormatter={v => formatValue(v)} tick={{ fontSize: 11, fill: '#94a3b8' }} width={56} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: '#e2e8f0' }}
            formatter={(v: unknown) => [formatValue(v), yKey.replace(/_/g, ' ')]}
          />
          <Bar dataKey={yKey} radius={[4, 4, 0, 0]}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
