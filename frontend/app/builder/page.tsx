"use client";

import { useEffect, useMemo, useState } from "react";
import { getApiBase } from "../lib/apiBase";

type Topic = { id: string; name: string; description: string };

type SearchResult = {
  chunk_id: string;
  document_id: string;
  title: string;
  url: string;
  source: string;
  published_at: string;
  snippet: string;
  score: number;
  topic_match: boolean;
};

type SearchResponse = { active_topic: { id: string; name: string } | null; results: SearchResult[] };

type BuilderCitation = {
  document_id: string;
  title: string;
  url: string;
  source: string;
  chunk_id: string;
  snippet: string;
};

type ReimplementResponse = { plan_md: string; citations: BuilderCitation[] };
type CompareResponse = { comparison_md: string; citations: BuilderCitation[] };

type PickerOption = { document_id: string; title: string; source: string; url: string };

const apiBase = getApiBase();

export default function BuilderPage() {
  const [tab, setTab] = useState<"reimplement" | "compare">("reimplement");
  const [topics, setTopics] = useState<Topic[]>([]);
  const [paperQuery, setPaperQuery] = useState("rag benchmark");
  const [paperOptions, setPaperOptions] = useState<PickerOption[]>([]);
  const [loadingPapers, setLoadingPapers] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [reTopic, setReTopic] = useState("");
  const [rePaperId, setRePaperId] = useState("");
  const [goal, setGoal] = useState("reproduce baseline results");
  const [timeHours, setTimeHours] = useState(6);
  const [compute, setCompute] = useState("single_gpu");
  const [reResult, setReResult] = useState<ReimplementResponse | null>(null);
  const [runningRe, setRunningRe] = useState(false);

  const [cmpModeA, setCmpModeA] = useState<"topic" | "paper">("topic");
  const [cmpModeB, setCmpModeB] = useState<"topic" | "paper">("topic");
  const [cmpTopicA, setCmpTopicA] = useState("");
  const [cmpTopicB, setCmpTopicB] = useState("");
  const [cmpPaperA, setCmpPaperA] = useState("");
  const [cmpPaperB, setCmpPaperB] = useState("");
  const [cmpResult, setCmpResult] = useState<CompareResponse | null>(null);
  const [runningCmp, setRunningCmp] = useState(false);

  useEffect(() => {
    void loadTopics();
  }, []);

  const selectedPaperTitle = useMemo(() => {
    const found = paperOptions.find((p) => p.document_id === rePaperId);
    return found?.title ?? "";
  }, [paperOptions, rePaperId]);

  async function loadTopics() {
    try {
      const res = await fetch(`${apiBase}/topics`);
      if (!res.ok) {
        return;
      }
      const data = (await res.json()) as Topic[];
      setTopics(data);
      if (data.length > 0) {
        setReTopic((prev) => prev || data[0].name);
        setCmpTopicA((prev) => prev || data[0].name);
        setCmpTopicB((prev) => prev || data[Math.min(1, data.length - 1)].name);
      }
    } catch {
      // Keep UI usable without topics endpoint.
    }
  }

  async function searchPapers() {
    setLoadingPapers(true);
    setError(null);
    try {
      const params = new URLSearchParams({ q: paperQuery, k: "20" });
      const res = await fetch(`${apiBase}/search?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`Paper search failed (${res.status})`);
      }
      const data = (await res.json()) as SearchResponse;
      const dedup = new Map<string, PickerOption>();
      for (const item of data.results) {
        if (!dedup.has(item.document_id)) {
          dedup.set(item.document_id, {
            document_id: item.document_id,
            title: item.title,
            source: item.source,
            url: item.url
          });
        }
      }
      setPaperOptions(Array.from(dedup.values()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Paper search failed");
    } finally {
      setLoadingPapers(false);
    }
  }

  async function runReimplement() {
    setRunningRe(true);
    setError(null);
    try {
      const payload = {
        topic: reTopic || null,
        paper_id: rePaperId || null,
        goal,
        constraints: { time_hours: timeHours, compute },
        k: 10
      };
      const res = await fetch(`${apiBase}/reimplement`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        throw new Error(`Reimplement failed (${res.status})`);
      }
      const data = (await res.json()) as ReimplementResponse;
      setReResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reimplement failed");
    } finally {
      setRunningRe(false);
    }
  }

  async function runCompare() {
    setRunningCmp(true);
    setError(null);
    try {
      const a = cmpModeA === "topic" ? { topic: cmpTopicA || null } : { paper_id: cmpPaperA || null };
      const b = cmpModeB === "topic" ? { topic: cmpTopicB || null } : { paper_id: cmpPaperB || null };
      const res = await fetch(`${apiBase}/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ a, b, constraints: { time_hours: timeHours, compute }, k: 8 })
      });
      if (!res.ok) {
        throw new Error(`Compare failed (${res.status})`);
      }
      const data = (await res.json()) as CompareResponse;
      setCmpResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Compare failed");
    } finally {
      setRunningCmp(false);
    }
  }

  async function copyMarkdown(value: string) {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      setError("Clipboard copy failed");
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-6 md:px-8 md:py-10">
      <header className="rounded-2xl border border-slate-300/90 bg-white/70 p-6 backdrop-blur-sm">
        <h1 className="text-3xl font-semibold">Builder</h1>
        <p className="mt-2 text-sm text-slate-600">Reimplementation and side-by-side comparison assistant.</p>
      </header>

      <div className="mt-4 flex gap-2">
        <button
          className={`rounded-md px-4 py-2 text-sm transition ${tab === "reimplement" ? "bg-[#8FC0A9] text-white" : "bg-white/70 text-slate-800 hover:bg-white"}`}
          onClick={() => setTab("reimplement")}
        >
          Reimplement
        </button>
        <button
          className={`rounded-md px-4 py-2 text-sm transition ${tab === "compare" ? "bg-[#8FC0A9] text-white" : "bg-white/70 text-slate-800 hover:bg-white"}`}
          onClick={() => setTab("compare")}
        >
          Compare
        </button>
      </div>

      <section className="mt-4 rounded-2xl border border-slate-300/90 bg-[var(--card)] p-4 backdrop-blur-sm space-y-4">
        <div className="grid gap-2 md:grid-cols-[1fr_auto]">
          <input
            className="rounded-md border border-slate-300 bg-white/80 px-3 py-2 text-sm"
            value={paperQuery}
            onChange={(e) => setPaperQuery(e.target.value)}
            placeholder="Search papers for picker"
          />
          <button className="rounded-md bg-[#68B0AB] px-4 py-2 text-sm text-white hover:bg-[#4A7C59]" onClick={searchPapers}>
            {loadingPapers ? "Searching..." : "Find Papers"}
          </button>
        </div>

        {tab === "reimplement" && (
          <div className="space-y-3">
            <select className="w-full rounded-md border border-slate-300 bg-white/80 px-3 py-2 text-sm" value={reTopic} onChange={(e) => setReTopic(e.target.value)}>
              <option value="">All topics</option>
              {topics.map((t) => (
                <option key={t.id} value={t.name}>
                  {t.name}
                </option>
              ))}
            </select>
            <select className="w-full rounded-md border border-slate-300 bg-white/80 px-3 py-2 text-sm" value={rePaperId} onChange={(e) => setRePaperId(e.target.value)}>
              <option value="">No specific paper</option>
              {paperOptions.map((p) => (
                <option key={p.document_id} value={p.document_id}>
                  {p.title}
                </option>
              ))}
            </select>
            <textarea className="w-full rounded-md border border-slate-300 bg-white/80 px-3 py-2 text-sm" rows={3} value={goal} onChange={(e) => setGoal(e.target.value)} />
            <div className="grid gap-2 sm:grid-cols-2">
              <input
                type="number"
                className="rounded-md border border-slate-300 bg-white/80 px-3 py-2 text-sm"
                value={timeHours}
                onChange={(e) => setTimeHours(Number(e.target.value) || 0)}
                placeholder="time_hours"
              />
              <input className="rounded-md border border-slate-300 bg-white/80 px-3 py-2 text-sm" value={compute} onChange={(e) => setCompute(e.target.value)} placeholder="compute" />
            </div>
            <button className="rounded-md bg-[#68B0AB] px-4 py-2 text-sm text-white hover:bg-[#4A7C59]" onClick={runReimplement}>
              {runningRe ? "Running..." : "Run Reimplement"}
            </button>

            {reResult && (
              <div className="space-y-3 rounded-md border border-slate-300 bg-white/80 p-3">
                {selectedPaperTitle && <p className="text-xs text-slate-500">Paper: {selectedPaperTitle}</p>}
                <button className="rounded bg-white/70 px-3 py-1 text-xs text-slate-700 hover:bg-white" onClick={() => copyMarkdown(reResult.plan_md)}>
                  Copy Markdown
                </button>
                <pre className="whitespace-pre-wrap text-sm text-slate-800">{reResult.plan_md}</pre>
                <ul className="space-y-2 text-sm">
                  {reResult.citations.map((c) => (
                    <li key={c.chunk_id} className="rounded border border-slate-300 p-2">
                      <a href={c.url} target="_blank" rel="noreferrer" className="underline">
                        {c.title}
                      </a>
                      <p className="text-xs text-slate-500">{c.source}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {tab === "compare" && (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2 rounded-md border border-slate-300 bg-white/70 p-3">
                <p className="text-sm font-medium">A</p>
                <select className="w-full rounded-md border border-slate-300 bg-white/80 px-3 py-2 text-sm" value={cmpModeA} onChange={(e) => setCmpModeA(e.target.value as "topic" | "paper")}>
                  <option value="topic">Topic</option>
                  <option value="paper">Paper</option>
                </select>
                {cmpModeA === "topic" ? (
                  <select className="w-full rounded-md border border-slate-300 bg-white/80 px-3 py-2 text-sm" value={cmpTopicA} onChange={(e) => setCmpTopicA(e.target.value)}>
                    <option value="">Select topic</option>
                    {topics.map((t) => (
                      <option key={t.id} value={t.name}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <select className="w-full rounded-md border border-slate-300 bg-white/80 px-3 py-2 text-sm" value={cmpPaperA} onChange={(e) => setCmpPaperA(e.target.value)}>
                    <option value="">Select paper</option>
                    {paperOptions.map((p) => (
                      <option key={p.document_id} value={p.document_id}>
                        {p.title}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="space-y-2 rounded-md border border-slate-300 bg-white/70 p-3">
                <p className="text-sm font-medium">B</p>
                <select className="w-full rounded-md border border-slate-300 bg-white/80 px-3 py-2 text-sm" value={cmpModeB} onChange={(e) => setCmpModeB(e.target.value as "topic" | "paper")}>
                  <option value="topic">Topic</option>
                  <option value="paper">Paper</option>
                </select>
                {cmpModeB === "topic" ? (
                  <select className="w-full rounded-md border border-slate-300 bg-white/80 px-3 py-2 text-sm" value={cmpTopicB} onChange={(e) => setCmpTopicB(e.target.value)}>
                    <option value="">Select topic</option>
                    {topics.map((t) => (
                      <option key={t.id} value={t.name}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <select className="w-full rounded-md border border-slate-300 bg-white/80 px-3 py-2 text-sm" value={cmpPaperB} onChange={(e) => setCmpPaperB(e.target.value)}>
                    <option value="">Select paper</option>
                    {paperOptions.map((p) => (
                      <option key={p.document_id} value={p.document_id}>
                        {p.title}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            <button className="rounded-md bg-[#68B0AB] px-4 py-2 text-sm text-white hover:bg-[#4A7C59]" onClick={runCompare}>
              {runningCmp ? "Running..." : "Run Compare"}
            </button>

            {cmpResult && (
              <div className="space-y-3 rounded-md border border-slate-300 bg-white/80 p-3">
                <button className="rounded bg-white/70 px-3 py-1 text-xs text-slate-700 hover:bg-white" onClick={() => copyMarkdown(cmpResult.comparison_md)}>
                  Copy Markdown
                </button>
                <pre className="whitespace-pre-wrap text-sm text-slate-800">{cmpResult.comparison_md}</pre>
                <ul className="space-y-2 text-sm">
                  {cmpResult.citations.map((c) => (
                    <li key={c.chunk_id} className="rounded border border-slate-300 p-2">
                      <a href={c.url} target="_blank" rel="noreferrer" className="underline">
                        {c.title}
                      </a>
                      <p className="text-xs text-slate-500">{c.source}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </section>

      {error && <p className="mt-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    </main>
  );
}
