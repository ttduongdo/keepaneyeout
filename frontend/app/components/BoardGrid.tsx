"use client";

import Link from "next/link";

type BoardGridProps = {
  boards: { id: string; name: string; count?: number }[];
};

export default function BoardGrid({ boards }: BoardGridProps) {
  if (boards.length === 0) {
    return <p className="text-sm text-slate-500">No boards yet.</p>;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {boards.map((board) => (
        <Link
          key={board.id}
          href={`/boards/${board.id}`}
          className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-[0_8px_20px_rgba(15,23,42,0.06)] transition hover:-translate-y-1"
        >
          <div className="text-sm text-slate-500">Board</div>
          <div className="mt-1 text-lg font-semibold text-slate-900">{board.name}</div>
          {typeof board.count === "number" && (
            <div className="mt-2 text-xs text-slate-500">{board.count} saved papers</div>
          )}
        </Link>
      ))}
    </div>
  );
}
