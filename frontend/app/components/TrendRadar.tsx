"use client";

import { useEffect, useState } from "react";

import type { TrendTopic } from "../lib/api";
import { fetchTrends } from "../lib/api";

type TrendRadarProps = {
  activeTopic?: string | null;
  onSelect: (topic: string | null) => void;
};

export default function TrendRadar({ activeTopic, onSelect }: TrendRadarProps) {
  const [trends, setTrends] = useState<TrendTopic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadTrends();
  }, []);

  async function loadTrends() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchTrends();
      setTrends(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load trends");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">Trend Radar</h3>
        <button className="text-xs text-slate-500 hover:text-slate-700" onClick={() => onSelect(null)}>
          Clear
        </button>
      </div>
      {loading && <div className="h-20 animate-pulse rounded-xl bg-white/70" />}
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="space-y-2">
        {trends.map((trend) => {
          const isActive = activeTopic === trend.topic;
          return (
            <button
              key={trend.topic}
              onClick={() => onSelect(trend.topic)}
              className={`w-full rounded-xl px-3 py-3 text-left text-xs transition ${
                isActive ? "bg-[#8FC0A9] text-white" : "bg-white/70 text-slate-700 hover:bg-white"
              }`}
            >
              <div className="text-sm font-semibold">{trend.topic}</div>
              <div className="mt-1 text-[11px] opacity-80">
                {trend.size} posts · {trend.growth_rate.toFixed(1)}x growth
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
