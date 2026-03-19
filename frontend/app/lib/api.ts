export type Post = {
  id: string;
  title: string;
  summary?: string | null;
  source: string;
  authors: string[];
  url?: string | null;
  published_at: string;
  ingested_at: string;
  thumbnail_url?: string | null;
  topic_cluster?: string | null;
  topics?: string[];
};

export type Board = {
  id: string;
  name: string;
  created_at?: string;
};

export type TrendTopic = {
  topic: string;
  size: number;
  growth_rate: number;
  posts: Array<Record<string, unknown>>;
};

export type TrendTimeseries = Record<string, { date: string; count: number }[]>;

import { authFetch } from "./auth";

export type PostFeedResponse = {
  items: Post[];
  page: number;
  has_more: boolean;
};

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${apiBase}${path}`, init);
  if (!res.ok) {
    throw new Error(`Request failed (${res.status})`);
  }
  return (await res.json()) as T;
}

async function fetchJsonAuth<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await authFetch(path, init);
  if (!res.ok) {
    throw new Error(`Request failed (${res.status})`);
  }
  return (await res.json()) as T;
}

export async function fetchPostFeed(params: {
  section?: string;
  page?: number;
  pageSize?: number;
  boardId?: string | null;
  topicClusters?: string[];
}): Promise<PostFeedResponse> {
  const query = new URLSearchParams();
  if (params.section) query.set("section", params.section);
  if (params.page) query.set("page", String(params.page));
  if (params.pageSize) query.set("page_size", String(params.pageSize));
  if (params.boardId) query.set("board_id", params.boardId);
  if (params.topicClusters && params.topicClusters.length > 0) {
    query.set("topic_cluster", params.topicClusters.join(","));
  }
  return fetchJsonAuth<PostFeedResponse>(`/posts?${query.toString()}`);
}

export async function fetchBoardPosts(boardId: string): Promise<Post[]> {
  const query = new URLSearchParams({ board_id: boardId, page_size: "100" });
  const data = await fetchJsonAuth<PostFeedResponse>(`/posts?${query.toString()}`);
  return data.items;
}

export async function fetchBoards(authFetch: (input: RequestInfo, init?: RequestInit) => Promise<Response>): Promise<Board[]> {
  const res = await authFetch("/boards");
  if (!res.ok) {
    throw new Error(`Boards failed (${res.status})`);
  }
  return (await res.json()) as Board[];
}

export async function savePostToBoard(
  authFetch: (input: RequestInfo, init?: RequestInit) => Promise<Response>,
  boardId: string,
  postId: string
): Promise<void> {
  const res = await authFetch(`/boards/${boardId}/save_post`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ post_id: postId })
  });
  if (!res.ok) {
    throw new Error(`Save failed (${res.status})`);
  }
}

export async function fetchTrends(): Promise<TrendTopic[]> {
  return fetchJson<TrendTopic[]>("/trends");
}

export async function fetchTrendTimeseries(range?: string): Promise<TrendTimeseries> {
  const params = range ? `?range=${encodeURIComponent(range)}` : "";
  return fetchJson<TrendTimeseries>(`/trends/timeseries${params}`);
}
