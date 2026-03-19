"use client";

import { formatDistanceToNow } from "date-fns";

import type { Post } from "../lib/api";
import { getTopicColor, isDarkColor } from "../lib/topicColors";

type PostCardProps = {
  post: Post;
  onSave: (post: Post) => void;
};

export default function PostCard({ post, onSave }: PostCardProps) {
  const published = post.published_at ? formatDistanceToNow(new Date(post.published_at), { addSuffix: true }) : "";
  const sourceLabel = post.source === "arxiv" ? "arXiv" : post.source === "hackernews" ? "Hacker News" : post.source;
  const primaryTopic = post.topic_cluster || post.topics?.[0] || null;
  const topicColor = getTopicColor(primaryTopic);
  const topicLabel = primaryTopic || "General";
  const darkBg = isDarkColor(topicColor);
  const titleColor = darkBg ? "#ffffff" : "#0f172a";
  const summaryColor = darkBg ? "rgba(255,255,255,0.8)" : "#475569";
  const metaColor = darkBg ? "rgba(255,255,255,0.7)" : "#64748b";

  function handleOpen() {
    if (!post.url) {
      return;
    }
    window.open(post.url, "_blank", "noopener,noreferrer");
  }

  return (
    <article
      className="group relative cursor-pointer rounded-2xl px-4 py-3 shadow-sm transition hover:-translate-y-1 hover:shadow-md"
      style={{ backgroundColor: topicColor }}
      onClick={handleOpen}
    >
      <div className="pointer-events-none absolute inset-0 rounded-2xl bg-black/10 opacity-0 transition-opacity group-hover:opacity-100" />
      <button
        onClick={(event) => {
          event.stopPropagation();
          onSave(post);
        }}
        className="absolute right-3 top-3 z-20 rounded-lg bg-white/90 px-3 py-1 text-sm font-medium text-slate-700 opacity-0 shadow-sm transition-opacity group-hover:opacity-100"
        aria-label="Save post"
      >
        Save
      </button>
      <div className="relative z-10 space-y-2" style={{ color: titleColor }}>
        <h3 className="text-base font-semibold">{post.title}</h3>
        {post.summary && (
          <p
            className="text-sm"
            style={{
              color: summaryColor,
              display: "-webkit-box",
              WebkitBoxOrient: "vertical",
              WebkitLineClamp: 4,
              overflow: "hidden"
            }}
          >
            {post.summary}
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <span
            className="chip-pill rounded-full px-2 py-1 text-sm font-medium"
          >
            {topicLabel}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="uppercase tracking-wide" style={{ color: metaColor }}>
            {sourceLabel}
          </span>
          <span style={{ color: metaColor }}>{published}</span>
        </div>
      </div>
    </article>
  );
}
