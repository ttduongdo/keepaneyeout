"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { fetchTrends, fetchTrendTimeseries, TrendTimeseries, TrendTopic } from "../lib/api";
import { useTopics } from "../hooks/useTopics";
import GrowthBarChart from "./GrowthBarChart";
import HeroTrendGraph from "./HeroTrendGraph";
import TrendList from "./TrendList";

const RANGE_OPTIONS = [
  { label: "24H", value: "24h" },
  { label: "7D", value: "7d" },
  { label: "30D", value: "30d" }
];

export default function TrendDashboard() {
  const [trends, setTrends] = useState<TrendTopic[]>([]);
  const [series, setSeries] = useState<TrendTimeseries>({});
  const [activeTopic, setActiveTopic] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState("7d");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const { selectedTopics, subscribedTopics } = useTopics();

  useEffect(() => {
    void loadData();
  }, [timeRange]);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [trendData, seriesData] = await Promise.all([fetchTrends(), fetchTrendTimeseries(timeRange)]);
      setTrends(trendData);
      setSeries(seriesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load trends");
    } finally {
      setLoading(false);
    }
  }

  const topTopics = useMemo(() => {
    return [...trends].sort((a, b) => b.size - a.size).slice(0, 5).map((t) => t.topic);
  }, [trends]);

  const chartData = useMemo(() => {
    const dateSet = new Set<string>();
    topTopics.forEach((topic) => {
      (series[topic] || []).forEach((point) => dateSet.add(point.date));
    });
    const dates = Array.from(dateSet).sort();
    return dates.map((date) => {
      const row: Record<string, number | string> = { date };
      topTopics.forEach((topic) => {
        const match = (series[topic] || []).find((point) => point.date === date);
        row[topic] = match?.count ?? 0;
      });
      return row;
    });
  }, [series, topTopics]);

  const highlightTopics = selectedTopics.length > 0 ? selectedTopics : subscribedTopics;

  function handleSelect(topic: string) {
    router.push(`/papers/search?q=${encodeURIComponent(topic)}`);
  }

  if (loading) {
    return <div className="h-72 rounded-2xl bg-white/70 p-4 text-sm text-slate-500">Loading trends...</div>;
  }

  if (error) {
    return <div className="rounded-2xl bg-white/70 p-4 text-sm text-red-600">{error}</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-2xl font-semibold text-slate-900">Trend Radar</h2>
        <div className="flex items-center gap-2">
          {RANGE_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => setTimeRange(option.value)}
              className={`rounded-lg px-3 py-1 text-sm font-medium transition ${
                timeRange === option.value ? "bg-[#8FC0A9] text-white" : "bg-white/70 text-slate-700 hover:bg-white"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <HeroTrendGraph
        chartData={chartData}
        topics={topTopics}
        activeTopic={activeTopic}
        highlightTopics={highlightTopics}
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <TrendList
          trends={trends}
          series={series}
          activeTopic={activeTopic}
          highlightTopics={highlightTopics}
          onHover={setActiveTopic}
          onClick={handleSelect}
        />
        <GrowthBarChart trends={trends} onClick={handleSelect} />
      </div>
    </div>
  );
}
