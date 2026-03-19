"use client";

import { useEffect, useMemo, useState } from "react";

import type { Paper } from "./PaperCard";
import type { Post } from "../lib/api";
import { authFetch } from "../lib/auth";

type SaveToBoardModalProps = {
  paper?: Paper | null;
  post?: Post | null;
  isOpen: boolean;
  onClose: () => void;
};

export default function SaveToBoardModal({ paper, post, isOpen, onClose }: SaveToBoardModalProps) {
  const [boards, setBoards] = useState<{ id: string; name: string }[]>([]);
  const [newBoard, setNewBoard] = useState("");
  const [error, setError] = useState<string | null>(null);

  const item = post ?? paper ?? null;
  const title = useMemo(() => item?.title ?? "", [item]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    void loadBoards();
  }, [isOpen]);

  async function loadBoards() {
    try {
      const res = await authFetch("/boards");
      if (!res.ok) {
        return;
      }
      const data = (await res.json()) as { id: string; name: string }[];
      setBoards(data);
    } catch {
      // ignore
    }
  }

  if (!isOpen) {
    return null;
  }

  function addBoard() {
    const trimmed = newBoard.trim();
    if (!trimmed) {
      return;
    }
    void createBoard(trimmed);
  }

  async function createBoard(name: string) {
    setError(null);
    try {
      const res = await authFetch("/boards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name })
      });
      if (!res.ok) {
        throw new Error(`Create board failed (${res.status})`);
      }
      const data = (await res.json()) as { id: string; name: string };
      setBoards((prev) => [...prev, data]);
      setNewBoard("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create board failed");
    }
  }


  async function saveToBoard(boardId: string) {
    if (!item) {
      return;
    }
    setError(null);
    try {
      const endpoint = post ? `/boards/${boardId}/save_post` : `/boards/${boardId}/papers`;
      const payload = post ? { post_id: item.id } : { paper_id: item.id };
      const res = await authFetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        throw new Error(`Save failed (${res.status})`);
      }
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Save to Board</h3>
          <button onClick={onClose} className="text-sm text-slate-500 hover:text-slate-700">
            Close
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-500">{title}</p>

        <div className="mt-4 space-y-2">
          {boards.length === 0 && <p className="text-sm text-slate-500">No boards yet.</p>}
          {boards.map((board) => (
            <button
              key={board.id}
              className="flex w-full items-center justify-between rounded bg-slate-50 px-3 py-2 text-sm hover:bg-slate-100"
              onClick={() => saveToBoard(board.id)}
            >
              {board.name}
              <span className="text-xs text-slate-400">Save</span>
            </button>
          ))}
        </div>

        <div className="mt-4 flex gap-2">
          <input
            className="flex-1 rounded bg-white/80 px-3 py-2 text-sm text-slate-700 focus:outline-none"
            value={newBoard}
            onChange={(e) => setNewBoard(e.target.value)}
            placeholder="Create new board"
          />
          <button onClick={addBoard} className="rounded bg-[#68B0AB] px-3 py-2 text-sm text-white hover:bg-[#4A7C59]">
            Add
          </button>
        </div>
        {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
      </div>
    </div>
  );
}
