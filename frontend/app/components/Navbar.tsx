"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import UserMenu from "./UserMenu";
import { useTheme } from "../hooks/useTheme";

type NavbarProps = {
  searchQuery?: string;
  onSearchChange?: (value: string) => void;
  onSearchSubmit?: (value: string) => void;
};

export default function Navbar({ searchQuery, onSearchChange, onSearchSubmit }: NavbarProps) {
  const [internalQuery, setInternalQuery] = useState("");
  const queryValue = searchQuery ?? internalQuery;
  const { theme, toggleTheme } = useTheme();

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = queryValue.trim();
    if (!trimmed) {
      return;
    }
    if (onSearchSubmit) {
      onSearchSubmit(trimmed);
      return;
    }
    window.location.href = `/papers/search?q=${encodeURIComponent(trimmed)}`;
  }

  function handleChange(value: string) {
    if (onSearchChange) {
      onSearchChange(value);
      return;
    }
    setInternalQuery(value);
  }

  return (
    <nav className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
      <div className="mx-auto flex w-full max-w-[1500px] items-center gap-4 px-4 py-4 md:px-8">
        <Link href="/" className="text-lg font-semibold text-slate-900">
          Pinsight
        </Link>
        <form onSubmit={handleSubmit} className="flex flex-1 items-center">
          <input
            className="w-full rounded-lg bg-white/70 px-4 py-2 text-sm font-medium text-slate-700 transition hover:brightness-95 focus:outline-none focus:brightness-95 dark:bg-slate-900/70 dark:text-slate-100 dark:hover:brightness-125 dark:focus:brightness-125 dark:hover:shadow-[0_0_18px_rgba(148,163,184,0.35)] dark:focus:shadow-[0_0_18px_rgba(148,163,184,0.45)]"
            placeholder="Search posts or topics"
            value={queryValue}
            onChange={(e) => handleChange(e.target.value)}
            onFocus={(e) => e.currentTarget.select()}
          />
        </form>
        <button
          type="button"
          onClick={toggleTheme}
          className="rounded-lg bg-white/70 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-white"
          aria-label="Toggle dark mode"
        >
          {theme === "dark" ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M12 3v2M12 19v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M3 12h2M19 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
              <circle cx="12" cy="12" r="4.5" stroke="currentColor" strokeWidth="1.8" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path
                d="M20 14.5A7.5 7.5 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5Z"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </button>
        <Link href="/boards" className="rounded-lg bg-white/70 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-white">
          Boards
        </Link>
        <UserMenu />
      </div>
    </nav>
  );
}
