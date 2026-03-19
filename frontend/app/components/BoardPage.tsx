"use client";

import { useEffect, useState } from "react";
import Masonry from "react-masonry-css";

import type { Post, PostFeedResponse } from "../lib/api";
import PostCard from "./PostCard";
import SaveToBoardModal from "./SaveToBoardModal";
import { authFetch } from "../lib/auth";
import { MASONRY_BREAKPOINTS } from "../lib/masonry";

type BoardPageProps = {
  name: string;
  boardId: string;
};

export default function BoardPage({ name, boardId }: BoardPageProps) {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveModalPost, setSaveModalPost] = useState<Post | null>(null);

  useEffect(() => {
    void loadPosts();
  }, [boardId]);

  async function loadPosts() {
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch(`/posts?board_id=${boardId}&page=1&page_size=50`);
      if (!res.ok) {
        throw new Error(`Failed to load board posts (${res.status})`);
      }
      const data = (await res.json()) as PostFeedResponse;
      setPosts(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load board posts");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-4">
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-500">Board</p>
        <h1 className="text-2xl font-semibold text-slate-900">{name}</h1>
      </div>

      {loading && <p className="text-sm text-slate-500">Loading posts...</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && posts.length === 0 && <p className="text-sm text-slate-500">No posts saved yet.</p>}

      {posts.length > 0 && (
        <Masonry breakpointCols={MASONRY_BREAKPOINTS} className="masonry-grid" columnClassName="masonry-column">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} onSave={(item) => setSaveModalPost(item)} />
          ))}
        </Masonry>
      )}

      <SaveToBoardModal post={saveModalPost} isOpen={saveModalPost !== null} onClose={() => setSaveModalPost(null)} />
    </section>
  );
}
