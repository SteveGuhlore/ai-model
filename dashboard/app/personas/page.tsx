"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Persona } from "@/lib/types";
import { useRouter } from "next/navigation";

export default function PersonasPage() {
  const [personas, setPersonas] = useState<Persona[] | null>(null);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [voice, setVoice] = useState("");
  const [consent, setConsent] = useState(false);
  const router = useRouter();

  async function load() {
    try {
      setPersonas(await api.listPersonas());
    } catch (e) {
      setError(String(e));
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function create() {
    setError("");
    if (!consent) {
      setError("Consent attestation is required to create a trainable persona.");
      return;
    }
    setCreating(true);
    try {
      await api.createPersona({
        name,
        brand_voice: voice,
        trigger_word: name.toLowerCase().replace(/\s+/g, ""),
        consent_attestation: consent,
      });
      setName("");
      setVoice("");
      setConsent(false);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-neutral-100">Personas</h1>
      <p className="mt-1 text-sm text-neutral-400">
        Each persona is trained on your own (or explicitly consented) likeness.
      </p>

      <section className="mt-6 rounded-card border border-surface-800 bg-surface-900 p-4">
        <h2 className="text-sm font-medium text-neutral-200">New persona</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="text-xs text-neutral-400">
            Name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-md border border-surface-700 bg-surface-950 px-3 py-2 text-sm text-neutral-100"
            />
          </label>
          <label className="text-xs text-neutral-400">
            Brand voice
            <input
              value={voice}
              onChange={(e) => setVoice(e.target.value)}
              placeholder="warm, upbeat, playful"
              className="mt-1 w-full rounded-md border border-surface-700 bg-surface-950 px-3 py-2 text-sm text-neutral-100"
            />
          </label>
        </div>
        <label className="mt-3 flex items-center gap-2 text-xs text-neutral-300">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
          />
          I confirm this likeness is my own or has explicit written consent.
        </label>
        <button
          onClick={create}
          disabled={creating || !name}
          className="mt-3 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-40"
        >
          {creating ? "Creating…" : "Create persona"}
        </button>
      </section>

      {error && <p className="mt-4 text-sm text-danger">{error}</p>}

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {personas === null ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="skeleton h-28" />
          ))
        ) : personas.length === 0 ? (
          <p className="text-sm text-neutral-500">
            No personas yet. Create one above, then generate content for it.
          </p>
        ) : (
          personas.map((p) => (
            <button
              key={p.id}
              onClick={() => router.push(`/generate?persona=${p.id}`)}
              className="rounded-card border border-surface-800 bg-surface-900 p-4 text-left hover:border-surface-700"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-neutral-100">{p.name}</span>
                <StatusDot status={p.status} />
              </div>
              <p className="mt-1 line-clamp-1 text-xs text-neutral-500">
                {p.brand_voice || "no brand voice set"}
              </p>
              <p className="mt-3 text-xs text-neutral-400">
                {p.likeness_lora_url ? "likeness trained" : "not trained yet"}
              </p>
            </button>
          ))
        )}
      </div>
    </div>
  );
}

function StatusDot({ status }: { status: Persona["status"] }) {
  const map: Record<Persona["status"], string> = {
    ready: "text-ok",
    training: "text-warn",
    failed: "text-danger",
    draft: "text-neutral-500",
  };
  return <span className={`text-xs ${map[status]}`}>{status}</span>;
}
