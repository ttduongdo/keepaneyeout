"use client";

import MasonryFeed from "./MasonryFeed";
import type { Paper } from "./PaperCard";

export type FeedSectionProps = {
  title: string;
  papers: Paper[];
  onLoadMore?: () => void;
  onSave: (paper: Paper) => void;
};

export default function FeedSection({ title, papers, onLoadMore, onSave }: FeedSectionProps) {
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <span className="text-xs text-slate-500">{papers.length} papers</span>
      </div>
      <MasonryFeed papers={papers} onLoadMore={onLoadMore} onSave={onSave} />
    </section>
  );
}
