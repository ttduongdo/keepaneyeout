"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Masonry from "react-masonry-css";

import type { Post } from "../lib/api";
import { fetchPostFeed } from "../lib/api";
import PostCard from "./PostCard";
import { MASONRY_BREAKPOINTS } from "../lib/masonry";

type PostFeedProps = {
  title: string;
  section: "recommended" | "latest" | "trending";
  topicClusters?: string[];
  excludeIds?: string[];
  onSave: (post: Post) => void;
};

export default function PostFeed({ title, section, topicClusters, excludeIds, onSave }: PostFeedProps) {
  const [posts, setPosts] = useState<Post[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  const clusterKey = useMemo(() => (topicClusters || []).join(","), [topicClusters]);
  const excludeKey = useMemo(() => (excludeIds || []).join(","), [excludeIds]);
  const excludeSet = useMemo(() => new Set(excludeIds || []), [excludeIds]);

  useEffect(() => {
    setPosts([]);
    setPage(1);
    setHasMore(true);
    void loadPosts(1, true);
  }, [section, clusterKey, excludeKey]);

  useEffect(() => {
    if (!hasMore || loading || posts.length === 0) {
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          void loadPosts(page + 1);
        }
      },
      { rootMargin: "200px" }
    );
    const node = sentinelRef.current;
    if (node) {
      observer.observe(node);
    }
    return () => observer.disconnect();
  }, [hasMore, loading, page, posts.length]);

  async function loadPosts(nextPage: number, reset = false) {
    if (loading && !reset) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPostFeed({
        section,
        page: nextPage,
        pageSize: 20,
        topicClusters
      });
      const filtered = excludeSet.size > 0 ? data.items.filter((item) => !excludeSet.has(item.id)) : data.items;
      setPosts((prev) => (reset ? filtered : [...prev, ...filtered]));
      setPage(data.page);
      setHasMore(data.has_more);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load posts");
    } finally {
      setLoading(false);
    }
  }

  if (loading && posts.length === 0) {
    return (
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
          <span className="text-xs text-slate-500">Loading...</span>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, idx) => (
            <div key={idx} className="h-52 animate-pulse rounded-2xl bg-white/60" />
          ))}
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <p className="text-sm text-red-600">{error}</p>
      </section>
    );
  }

  if (posts.length === 0) {
    return (
      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <p className="text-sm text-slate-500">No posts found for this section.</p>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <span className="text-xs text-slate-500">{posts.length} posts</span>
      </div>
      <Masonry breakpointCols={MASONRY_BREAKPOINTS} className="masonry-grid" columnClassName="masonry-column">
        {posts.map((post) => (
          <PostCard key={`${section}-${post.id}`} post={post} onSave={onSave} />
        ))}
      </Masonry>
      {hasMore && <div ref={sentinelRef} className="h-6 w-full" />}
    </section>
  );
}
