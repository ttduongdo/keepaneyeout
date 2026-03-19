"use client";

import { useEffect, useRef } from "react";
import Masonry from "react-masonry-css";

import PaperCard, { Paper } from "./PaperCard";
import { MASONRY_BREAKPOINTS } from "../lib/masonry";

export type MasonryFeedProps = {
  papers: Paper[];
  onLoadMore?: () => void;
  onSave: (paper: Paper) => void;
};

export default function MasonryFeed({ papers, onLoadMore, onSave }: MasonryFeedProps) {
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!onLoadMore) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          onLoadMore();
        }
      },
      { rootMargin: "200px" }
    );

    const node = sentinelRef.current;
    if (node) {
      observer.observe(node);
    }

    return () => {
      observer.disconnect();
    };
  }, [onLoadMore]);

  return (
    <>
      <Masonry breakpointCols={MASONRY_BREAKPOINTS} className="masonry-grid" columnClassName="masonry-column">
        {papers.map((paper) => (
          <PaperCard key={paper.id} paper={paper} onSave={onSave} />
        ))}
      </Masonry>
      <div ref={sentinelRef} className="h-6 w-full" />
    </>
  );
}
