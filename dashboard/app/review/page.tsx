"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Content } from "@/lib/types";
import { ReviewBadge, SafetyBadge } from "@/components/safety-badge";

const FILTERS = ["pending", "approved", "rejected"] as const;

export default function ReviewPage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("pending");
  const [items, setItems] = useState<Content[] | null>(null);
  const [error, setError] = useState("");
  const reqId = useRef(0);

  async function load() {
    const id = ++reqId.current; // ignore stale responses from rapid filter changes
    setItems(null);
    setError("");
    try {
      const got = await api.listContent({ review_status: filter });
      if (id === reqId.current) setItems(got);
    } catch (e) {
      if (id === reqId.current) {
        setError(String(e));
        setItems([]); // don't leave the grid stuck on the loading skeleton
      }
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  async function decide(id: string, status: "approved" | "rejected") {
    try {
      await api.review(id, status);
      setItems((prev) => (prev ? prev.filter((c) => c.id !== id) : prev));
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-neutral-100">Review queue</h1>
      <p className="mt-1 text-sm text-neutral-400">
        Approve content before it can be scheduled or published. Every asset has already
        passed the SFW safety gate; this is your editorial sign-off.
      </p>

      <div className="mt-4 flex gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium ${
              filter === f
                ? "bg-accent text-white"
                : "bg-surface-800 text-neutral-400 hover:text-neutral-100"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {items === null ? (
          Array.from({ length: 8 }).map((_, i) => <div key={i} className="skeleton aspect-[4/5]" />)
        ) : items.length === 0 ? (
          <p className="text-sm text-neutral-500">
            Nothing {filter}. Generate a batch, then approve the keepers here.
          </p>
        ) : (
          items.map((c) => (
            <article
              key={c.id}
              className="overflow-hidden rounded-card border border-surface-800 bg-surface-900"
            >
              <div className="bg-surface-950">
                {c.media_url ? (
                  c.kind === "video" ? (
                    <video src={c.media_url} className="aspect-[9/16] w-full" controls muted />
                  ) : (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={c.media_url} alt="" className="aspect-[4/5] w-full object-cover" />
                  )
                ) : (
                  <div className="skeleton aspect-[4/5]" />
                )}
              </div>
              <div className="space-y-2 p-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-neutral-500">{c.channel}</span>
                  <SafetyBadge status={c.safety_status} />
                </div>
                <p className="line-clamp-2 text-xs text-neutral-400">{c.prompt}</p>
                {filter === "pending" ? (
                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={() => decide(c.id, "approved")}
                      className="flex-1 rounded-md bg-ok/15 px-2 py-1.5 text-xs font-medium text-ok hover:bg-ok/25"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => decide(c.id, "rejected")}
                      className="flex-1 rounded-md bg-danger/15 px-2 py-1.5 text-xs font-medium text-danger hover:bg-danger/25"
                    >
                      Reject
                    </button>
                  </div>
                ) : (
                  <ReviewBadge status={c.review_status} />
                )}
              </div>
            </article>
          ))
        )}
      </div>
    </div>
  );
}
