"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, XAxis, YAxis } from "recharts";

import type { TrendTopic } from "../lib/api";
import { getTopicColor } from "../lib/topicColors";
import { useTheme } from "../hooks/useTheme";

type GrowthBarChartProps = {
  trends: TrendTopic[];
  onClick: (topic: string) => void;
};

function hexToRgba(hex: string, alpha: number) {
  const normalized = hex.replace("#", "");
  const num = parseInt(normalized, 16);
  const r = (num >> 16) & 0xff;
  const g = (num >> 8) & 0xff;
  const b = num & 0xff;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export default function GrowthBarChart({ trends, onClick }: GrowthBarChartProps) {
  const { theme } = useTheme();
  const tickFill = theme === "dark" ? "#e2e8f0" : "#334155";
  const data = [...trends]
    .sort((a, b) => b.growth_rate - a.growth_rate)
    .slice(0, 8)
    .map((trend) => {
      const color = getTopicColor(trend.topic);
      const opacity = Math.min(1, Math.max(0.35, trend.growth_rate / 3));
      return {
        topic: trend.topic,
        growth: trend.growth_rate,
        fill: hexToRgba(color, opacity)
      };
    });

  return (
    <div className="h-[340px] rounded-2xl border-2 border-slate-900 bg-white/70 p-4 shadow-sm">
      <h3 className="text-base font-semibold text-slate-800">Growth comparison</h3>
      <div className="mt-2 h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 16, right: 10 }} barCategoryGap={14} barGap={4}>
            <XAxis type="number" hide />
            <YAxis type="category" dataKey="topic" width={130} tick={{ fontSize: 13, fill: tickFill }} />
            <Bar
              dataKey="growth"
              onClick={(payload) => onClick(payload.payload.topic)}
              radius={[6, 6, 6, 6]}
              barSize={24}
              stroke="#0f172a"
              strokeWidth={1}
              isAnimationActive
              animationDuration={800}
              fillOpacity={1}
            >
              {data.map((entry) => (
                <Cell key={entry.topic} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
