"use client";

import { useEffect, useState } from "react";

import BoardPage from "../../components/BoardPage";
import Navbar from "../../components/Navbar";
import { authFetch, clearToken, getToken } from "../../lib/auth";

type BoardDetail = { id: string; name: string; papers: { id: string; title: string; published_date: string; url?: string }[] };

export default function BoardDetailPage({ params }: { params: { id: string } }) {
  const [board, setBoard] = useState<BoardDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      window.location.href = "/login";
      return;
    }
    void loadBoard();
  }, [params.id]);

  async function loadBoard() {
    setError(null);
    try {
      const res = await authFetch(`/boards/${params.id}`);
      if (res.status === 401) {
        clearToken();
        window.location.href = "/login";
        return;
      }
      if (!res.ok) {
        throw new Error("Board not found");
      }
      const data = (await res.json()) as BoardDetail;
      setBoard(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Board not found");
    }
  }

  return (
    <main className="min-h-screen bg-transparent">
      <Navbar />
      <div className="mx-auto max-w-4xl px-4 py-10">
        {error && <p className="text-sm text-red-600">{error}</p>}
        {board && <BoardPage name={board.name} boardId={board.id} />}
      </div>
    </main>
  );
}
