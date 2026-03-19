"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend, CartesianGrid, ReferenceDot } from "recharts";

import { getTopicColor } from "../lib/topicColors";

type HeroTrendGraphProps = {
  chartData: Array<Record<string, number | string>>;
  topics: string[];
  activeTopic: string | null;
  highlightTopics?: string[];
};

export default function HeroTrendGraph({ chartData, topics, activeTopic, highlightTopics = [] }: HeroTrendGraphProps) {
  const highlightSet = new Set(highlightTopics);

  return (
    <div className="h-[360px] w-full rounded-2xl border-2 border-slate-900 bg-white/80 p-4 shadow-sm">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="4 4" stroke="#C8D5B9" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          {topics.map((topic) => {
            const isActive = activeTopic ? activeTopic === topic : true;
            const isHighlighted = highlightSet.size > 0 ? highlightSet.has(topic) : true;
            const color = getTopicColor(topic);
            const opacity = isActive ? 1 : isHighlighted ? 0.6 : 0.2;
            return (
              <Line
                key={topic}
                type="monotone"
                dataKey={topic}
                stroke={color}
                strokeWidth={isActive ? 3 : 2}
                dot={false}
                strokeOpacity={opacity}
                isAnimationActive
                animationDuration={900}
              />
            );
          })}
          {topics.map((topic) => {
            const color = getTopicColor(topic);
            const maxPoint = chartData.reduce(
              (acc, row) => {
                const value = typeof row[topic] === "number" ? (row[topic] as number) : 0;
                return value > acc.value ? { date: row.date as string, value } : acc;
              },
              { date: "", value: 0 }
            );
            return maxPoint.date ? (
              <ReferenceDot key={`${topic}-peak`} x={maxPoint.date} y={maxPoint.value} r={4} fill={color} stroke="none" />
            ) : null;
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
