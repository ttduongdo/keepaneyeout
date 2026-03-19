"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { useAuth } from "../lib/useAuth";

export default function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  const initials = useMemo(() => {
    if (!user?.email) {
      return "ME";
    }
    return user.email.slice(0, 2).toUpperCase();
  }, [user?.email]);

  if (!user) {
    return (
      <Link href="/login" className="rounded-full bg-white/70 px-3 py-2 text-sm text-slate-700 hover:bg-white">
        Login
      </Link>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-300 bg-white text-xs font-semibold text-slate-600"
        aria-label="User menu"
      >
        {initials}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-40 rounded-xl border border-slate-200 bg-white shadow-lg">
          <Link
            href="/profile"
            className="block px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            onClick={() => setOpen(false)}
          >
            Profile
          </Link>
          <Link
            href="/boards"
            className="block px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            onClick={() => setOpen(false)}
          >
            My Boards
          </Link>
          <button
            onClick={() => {
              setOpen(false);
              void logout();
            }}
            className="block w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
          >
            Logout
          </button>
        </div>
      )}
    </div>
  );
}
