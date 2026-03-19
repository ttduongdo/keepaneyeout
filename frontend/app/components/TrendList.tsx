"use client";

import { Line, LineChart } from "recharts";

import type { TrendTimeseries, TrendTopic } from "../lib/api";
import { getTopicColor } from "../lib/topicColors";

type TrendListProps = {
  trends: TrendTopic[];
  series: TrendTimeseries;
  activeTopic: string | null;
  highlightTopics?: string[];
  onHover: (topic: string | null) => void;
  onClick: (topic: string) => void;
};

export default function TrendList({
  trends,
  series,
  activeTopic,
  highlightTopics = [],
  onHover,
  onClick
}: TrendListProps) {
  const highlightSet = new Set(highlightTopics);
  return (
    <div className="space-y-3 rounded-2xl border-2 border-slate-900 bg-white/70 p-4 shadow-sm">
      <h3 className="text-base font-semibold text-slate-800">Topics</h3>
      <ul className="space-y-2">
        {trends.map((trend) => {
          const isActive = activeTopic === trend.topic;
          const isHighlighted = highlightSet.has(trend.topic);
          const growthUp = trend.growth_rate >= 1;
          const data = (series[trend.topic] || []).slice(-7);
          const color = getTopicColor(trend.topic);

          return (
            <li
              key={trend.topic}
              onMouseEnter={() => onHover(trend.topic)}
              onMouseLeave={() => onHover(null)}
              onClick={() => onClick(trend.topic)}
              className={`flex cursor-pointer items-center justify-between gap-3 rounded-xl px-3 py-2 transition ${
                isActive || isHighlighted ? "bg-[#8FC0A9]/30" : "bg-white/60 hover:bg-white"
              }`}
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-base font-medium">
                  <span className="truncate">{trend.topic}</span>
                  <span className={`text-sm ${growthUp ? "text-emerald-600" : "text-rose-600"}`}>
                    {growthUp ? "▲" : "▼"}
                  </span>
                </div>
                <div className="text-sm text-slate-500">{trend.size} posts</div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium">{trend.growth_rate.toFixed(2)}x</span>
                <LineChart width={80} height={30} data={data}>
                  <Line type="monotone" dataKey="count" stroke={color} strokeWidth={2} dot={false} />
                </LineChart>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
