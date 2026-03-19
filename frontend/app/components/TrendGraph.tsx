"use client";

import { useEffect, useMemo, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { TrendTimeseries } from "../lib/api";
import { fetchTrendTimeseries } from "../lib/api";

type SeriesRow = Record<string, number | string>;

const COLORS = ["#0b6bcb", "#0284c7", "#38bdf8", "#64748b", "#0f172a"];

export default function TrendGraph() {
  const [data, setData] = useState<TrendTimeseries>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadTimeseries();
  }, []);

  async function loadTimeseries() {
    setLoading(true);
    setError(null);
    try {
      const series = await fetchTrendTimeseries();
      setData(series);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load trend graph");
    } finally {
      setLoading(false);
    }
  }

  const { chartData, topics } = useMemo(() => {
    const entries = Object.entries(data);
    if (entries.length === 0) {
      return { chartData: [], topics: [] as string[] };
    }
    const ranked = entries
      .map(([topic, points]) => ({
        topic,
        total: points.reduce((sum, point) => sum + (point.count ?? 0), 0)
      }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 4);

    const topics = ranked.map((item) => item.topic);
    const dateSet = new Set<string>();
    topics.forEach((topic) => {
      (data[topic] || []).forEach((point) => dateSet.add(point.date));
    });
    const dates = Array.from(dateSet).sort();

    const chartData: SeriesRow[] = dates.map((date) => {
      const row: SeriesRow = { date };
      topics.forEach((topic) => {
        const match = (data[topic] || []).find((point) => point.date === date);
        row[topic] = match?.count ?? 0;
      });
      return row;
    });

    return { chartData, topics };
  }, [data]);

  return (
    <section className="space-y-3">
      <h3 className="text-sm font-semibold text-slate-900">Trend Graph</h3>
      {loading && <div className="h-40 animate-pulse rounded-xl bg-white/70" />}
      {error && <p className="text-xs text-red-600">{error}</p>}
      {!loading && chartData.length === 0 && <p className="text-xs text-slate-500">No trend data yet.</p>}
      {!loading && chartData.length > 0 && (
        <div className="h-48 rounded-xl bg-white/80 p-2 shadow-sm">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              {topics.map((topic, idx) => (
                <Line key={topic} type="monotone" dataKey={topic} stroke={COLORS[idx % COLORS.length]} strokeWidth={2} dot={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
