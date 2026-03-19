"use client";

import { createContext, useContext, useMemo, useState } from "react";

type FeedFilterContextValue = {
  topicFilter: string | null;
  setTopicFilter: (topic: string | null) => void;
  clearTopicFilter: () => void;
};

const FeedFilterContext = createContext<FeedFilterContextValue | null>(null);

export function FeedFilterProvider({ children }: { children: React.ReactNode }) {
  const [topicFilter, setTopicFilter] = useState<string | null>(null);

  const value = useMemo(
    () => ({
      topicFilter,
      setTopicFilter,
      clearTopicFilter: () => setTopicFilter(null)
    }),
    [topicFilter]
  );

  return <FeedFilterContext.Provider value={value}>{children}</FeedFilterContext.Provider>;
}

export function useFeedFilter() {
  const ctx = useContext(FeedFilterContext);
  if (!ctx) {
    throw new Error("useFeedFilter must be used within FeedFilterProvider");
  }
  return ctx;
}
