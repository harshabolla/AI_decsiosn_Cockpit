'use client';

import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { KPI } from '@/types';

interface KPISectionProps {
  kpis: KPI[];
}

export function KPISection({ kpis }: KPISectionProps) {
  if (!kpis || kpis.length === 0) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 my-3">
      {kpis.map((kpi, idx) => {
        const isUp = kpi.trend_direction === 'up';
        const isDown = kpi.trend_direction === 'down';

        return (
          <div
            key={idx}
            className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 backdrop-blur shadow-sm hover:border-slate-700 transition-all"
          >
            <span className="text-[11px] font-medium text-slate-400 block truncate">
              {kpi.label}
            </span>
            <div className="flex items-baseline gap-1 mt-1.5">
              <span className="text-xl font-bold tracking-tight text-white">
                {kpi.value}
              </span>
              {kpi.unit && (
                <span className="text-xs font-normal text-slate-400">
                  {kpi.unit}
                </span>
              )}
            </div>

            {kpi.trend !== null && kpi.trend !== undefined && (
              <div className="flex items-center gap-1 mt-2 text-[11px]">
                {isUp && (
                  <span className="flex items-center text-emerald-400 font-medium">
                    <TrendingUp size={13} className="mr-0.5" />
                    +{kpi.trend}%
                  </span>
                )}
                {isDown && (
                  <span className="flex items-center text-rose-400 font-medium">
                    <TrendingDown size={13} className="mr-0.5" />
                    {kpi.trend}%
                  </span>
                )}
                {!isUp && !isDown && (
                  <span className="flex items-center text-slate-400 font-medium">
                    <Minus size={13} className="mr-0.5" />
                    {kpi.trend}%
                  </span>
                )}
                <span className="text-slate-500">vs prev period</span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
