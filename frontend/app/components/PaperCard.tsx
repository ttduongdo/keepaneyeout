"use client";

import Link from "next/link";

export type Paper = {
  id: string;
  title: string;
  authors: string[] | string;
  summary: string;
  tags?: string[];
  published_date: string;
  url?: string;
};

type PaperCardProps = {
  paper: Paper;
  onSave: (paper: Paper) => void;
};

export default function PaperCard({ paper, onSave }: PaperCardProps) {
  const authors = Array.isArray(paper.authors) ? paper.authors.join(", ") : paper.authors;
  const year = paper.published_date ? new Date(paper.published_date).getFullYear() : "";

  return (
    <article className="group relative mb-4 break-inside-avoid rounded-2xl bg-[#FAF3DD] p-4 shadow-sm transition hover:-translate-y-1 hover:shadow-md">
      <button
        onClick={() => onSave(paper)}
        className="absolute right-3 top-3 rounded-full bg-white/70 px-2 py-1 text-xs text-slate-700 opacity-0 transition-opacity group-hover:opacity-100"
        aria-label="Save paper"
      >
        Save
      </button>
      <div className="space-y-2">
        <Link href={`/papers/${paper.id}`} className="text-base font-semibold text-slate-900">
          {paper.title}
        </Link>
        <p className="text-xs text-slate-500">{authors || "Unknown authors"}</p>
        <p className="text-xs text-slate-500">{year ? `Published ${year}` : ""}</p>
        <p
          className="text-sm text-slate-700"
          style={{
            display: "-webkit-box",
            WebkitBoxOrient: "vertical",
            WebkitLineClamp: 3,
            overflow: "hidden"
          }}
        >
          {paper.summary}
        </p>
        {paper.tags && paper.tags.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {paper.tags.map((tag) => (
              <span key={tag} className="rounded-full bg-white/70 px-2 py-1 text-xs text-slate-600">
                {tag}
              </span>
            ))}
          </div>
        )}
        <div className="flex items-center justify-between pt-2">
          {paper.url ? (
            <a href={paper.url} target="_blank" rel="noreferrer" className="text-xs font-medium text-slate-900 underline">
              View Paper
            </a>
          ) : (
            <span className="text-xs text-slate-400">No URL</span>
          )}
          <span className="text-[11px] text-slate-400">AI Research Radar</span>
        </div>
      </div>
    </article>
  );
}
