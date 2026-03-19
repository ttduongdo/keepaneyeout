"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { authFetch, getToken } from "../lib/auth";

type TopicsContextValue = {
  selectedTopics: string[];
  subscribedTopics: string[];
  effectiveTopics: string[];
  setSelectedTopics: (topics: string[]) => void;
  clearSelectedTopics: () => void;
  addSubscribedTopic: (topic: string) => Promise<void>;
  removeSubscribedTopic: (topic: string) => Promise<void>;
  setSubscribedTopics: (topics: string[]) => Promise<void>;
};

const TopicsContext = createContext<TopicsContextValue | null>(null);

const STORAGE_KEY = "topics";
const MAX_TOPICS = 10;

function normalizeTopic(topic: string) {
  return topic.trim();
}

export function TopicsProvider({ children }: { children: React.ReactNode }) {
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [subscribedTopics, setSubscribedTopicsState] = useState<string[]>([]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const token = getToken();
    if (token) {
      void loadFromApi();
      return;
    }
    loadFromStorage();
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(subscribedTopics));
  }, [subscribedTopics]);

  async function loadFromApi() {
    try {
      const res = await authFetch("/user/topics");
      if (!res.ok) {
        loadFromStorage();
        return;
      }
      const data = (await res.json()) as { topics: string[] };
      setSubscribedTopicsState(Array.isArray(data.topics) ? data.topics : []);
    } catch {
      loadFromStorage();
    }
  }

  function loadFromStorage() {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      return;
    }
    try {
      const parsed = JSON.parse(stored) as string[];
      if (Array.isArray(parsed)) {
        setSubscribedTopicsState(parsed);
      }
    } catch {
      // ignore
    }
  }

  const value = useMemo<TopicsContextValue>(() => {
    const effectiveTopics = selectedTopics.length > 0 ? selectedTopics : subscribedTopics;

    const addSubscribedTopic = async (topic: string) => {
      const normalized = normalizeTopic(topic);
      if (!normalized) {
        return;
      }
      const res = await authFetch("/user/topics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: normalized })
      });
      if (!res.ok) {
        throw new Error("Failed to subscribe");
      }
      const data = (await res.json()) as { topics: string[] };
      setSubscribedTopicsState(Array.isArray(data.topics) ? data.topics : []);
    };

    const removeSubscribedTopic = async (topic: string) => {
      const normalized = normalizeTopic(topic);
      const res = await authFetch(`/user/topics/${encodeURIComponent(normalized)}`, { method: "DELETE" });
      if (!res.ok) {
        throw new Error("Failed to unsubscribe");
      }
      const data = (await res.json()) as { topics: string[] };
      const next = Array.isArray(data.topics) ? data.topics : [];
      setSubscribedTopicsState(next);
      setSelectedTopics((prev) => prev.filter((item) => item !== normalized));
    };

    const setSubscribedTopics = async (topics: string[]) => {
      const next = Array.from(new Set(topics.map(normalizeTopic).filter(Boolean))).slice(0, MAX_TOPICS);
      const res = await authFetch("/user/topics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topics: next })
      });
      if (!res.ok) {
        throw new Error("Failed to update topics");
      }
      const data = (await res.json()) as { topics: string[] };
      setSubscribedTopicsState(Array.isArray(data.topics) ? data.topics : next);
    };

    return {
      selectedTopics,
      subscribedTopics,
      effectiveTopics,
      setSelectedTopics,
      clearSelectedTopics: () => setSelectedTopics([]),
      addSubscribedTopic,
      removeSubscribedTopic,
      setSubscribedTopics
    };
  }, [selectedTopics, subscribedTopics]);

  return <TopicsContext.Provider value={value}>{children}</TopicsContext.Provider>;
}

export function useTopics() {
  const ctx = useContext(TopicsContext);
  if (!ctx) {
    throw new Error("useTopics must be used within TopicsProvider");
  }
  return ctx;
}
