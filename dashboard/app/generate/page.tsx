"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { Content, GenerateResult, Persona } from "@/lib/types";

const CHANNELS = [
  { id: "lifestyle", label: "Lifestyle / beach photos" },
  { id: "tiktok", label: "TikTok video (9:16)" },
];

const PLACEMENTS = ["ig_square", "ig_portrait", "tiktok", "reels", "meta_feed"];

function GenerateInner() {
  const params = useSearchParams();
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [personaId, setPersonaId] = useState(params.get("persona") || "");
  const [channel, setChannel] = useState("lifestyle");
  const [prompt, setPrompt] = useState("");
  const [placement, setPlacement] = useState("ig_square");
  const [count, setCount] = useState(4);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Content[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .listPersonas()
      .then((p) => {
        setPersonas(p);
        if (!personaId && p[0]) setPersonaId(p[0].id);
      })
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run() {
    setError("");
    setBusy(true);
    setResult(null);
    try {
      const { job_id } = await api.generate({
        persona_id: personaId,
        channel,
        prompt,
        placements: [channel === "tiktok" ? "tiktok" : placement],
        count,
      });
      // Generation runs as a background job; poll until it finishes.
      const res = await api.pollJob<GenerateResult>(job_id);
      setResult(res.content);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-neutral-100">Generate</h1>
      <p className="mt-1 text-sm text-neutral-400">
        Output lands in the review queue — nothing is published without your approval.
      </p>

      <section className="mt-6 grid gap-3 rounded-card border border-surface-800 bg-surface-900 p-4 sm:grid-cols-2">
        <label className="text-xs text-neutral-400">
          Persona
          <select
            value={personaId}
            onChange={(e) => setPersonaId(e.target.value)}
            className="mt-1 w-full rounded-md border border-surface-700 bg-surface-950 px-3 py-2 text-sm text-neutral-100"
          >
            <option value="">Select…</option>
            {personas.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-neutral-400">
          Channel
          <select
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            className="mt-1 w-full rounded-md border border-surface-700 bg-surface-950 px-3 py-2 text-sm text-neutral-100"
          >
            {CHANNELS.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-neutral-400 sm:col-span-2">
          Brief
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={2}
            placeholder="on a sunny beach at golden hour, candid smile"
            className="mt-1 w-full rounded-md border border-surface-700 bg-surface-950 px-3 py-2 text-sm text-neutral-100"
          />
        </label>
        {channel !== "tiktok" && (
          <label className="text-xs text-neutral-400">
            Placement
            <select
              value={placement}
              onChange={(e) => setPlacement(e.target.value)}
              className="mt-1 w-full rounded-md border border-surface-700 bg-surface-950 px-3 py-2 text-sm text-neutral-100"
            >
              {PLACEMENTS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="text-xs text-neutral-400">
          Count
          <input
            type="number"
            min={1}
            max={12}
            value={count}
            onChange={(e) =>
              // Clamp client-side too (the backend also bounds it 1..12).
              setCount(Math.min(12, Math.max(1, Math.floor(Number(e.target.value) || 1))))
            }
            className="mt-1 w-full rounded-md border border-surface-700 bg-surface-950 px-3 py-2 text-sm text-neutral-100"
          />
        </label>
        <div className="sm:col-span-2">
          <button
            onClick={run}
            disabled={busy || !personaId || !prompt}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-40"
          >
            {busy ? "Generating…" : "Generate batch"}
          </button>
        </div>
      </section>

      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      {busy && (
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Array.from({ length: count }).map((_, i) => (
            <div key={i} className="skeleton aspect-[4/5]" />
          ))}
        </div>
      )}

      {result && (
        <div className="mt-6">
          <p className="text-sm text-neutral-300">
            {result.length} item(s) passed screening and are now in the review queue.
            {result.length === 0 && " (Everything was blocked by the safety gate.)"}
          </p>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {result.map((c) => (
              <div key={c.id} className="overflow-hidden rounded-card border border-surface-800">
                {c.media_url &&
                  (c.kind === "video" ? (
                    <video src={c.media_url} className="aspect-[9/16] w-full" muted />
                  ) : (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={c.media_url} alt="" className="aspect-[4/5] w-full object-cover" />
                  ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function GeneratePage() {
  return (
    <Suspense fallback={<div className="skeleton h-64" />}>
      <GenerateInner />
    </Suspense>
  );
}
