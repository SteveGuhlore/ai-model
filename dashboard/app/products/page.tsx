"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { GenerateResult, Persona, Product } from "@/lib/types";

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const [busyAd, setBusyAd] = useState<string | null>(null);

  async function load() {
    try {
      setError("");
      const [prods, peeps] = await Promise.all([api.listProducts(), api.listPersonas()]);
      setProducts(prods);
      setPersonas(peeps);
    } catch (e) {
      setError(String(e));
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function create() {
    setError("");
    try {
      await api.createProduct({ name, category, description } as Partial<Product>);
      setName("");
      setCategory("");
      setDescription("");
      await load();
    } catch (e) {
      setError(String(e));
    }
  }

  async function makeAd(productId: string) {
    setStatus("");
    setError("");
    // Require a fully-trained persona — don't silently fall back to an untrained one.
    const persona = personas.find((p) => p.status === "ready");
    if (!persona) {
      setError("Train a persona (status 'ready') before generating product ads.");
      return;
    }
    setBusyAd(productId);
    try {
      setStatus("Generating ad creatives…");
      const { job_id } = await api.generateProductAd({
        persona_id: persona.id,
        product_id: productId,
        prompt: "studio product shot, clean background",
        placements: ["ig_portrait"],
        count: 4,
      });
      const res = await api.pollJob<GenerateResult>(job_id);
      setStatus(`${res.created} ad creative(s) sent to the review queue.`);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusyAd(null);
    }
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-neutral-100">Products</h1>
      <p className="mt-1 text-sm text-neutral-400">
        Dropship products your persona models in ad creatives (clothed apparel / intimates).
      </p>

      <section className="mt-6 grid gap-3 rounded-card border border-surface-800 bg-surface-900 p-4 sm:grid-cols-3">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Product name"
          className="rounded-md border border-surface-700 bg-surface-950 px-3 py-2 text-sm text-neutral-100"
        />
        <input
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          placeholder="Category (e.g. intimates)"
          className="rounded-md border border-surface-700 bg-surface-950 px-3 py-2 text-sm text-neutral-100"
        />
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Short description"
          className="rounded-md border border-surface-700 bg-surface-950 px-3 py-2 text-sm text-neutral-100"
        />
        <button
          onClick={create}
          disabled={!name}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-40"
        >
          Add product
        </button>
      </section>

      {error && <p className="mt-4 text-sm text-danger">{error}</p>}
      {status && <p className="mt-4 text-sm text-ok">{status}</p>}

      <ul className="mt-6 space-y-2">
        {products.length === 0 ? (
          <li className="text-sm text-neutral-500">
            No products yet. Add one above to generate ads with your persona.
          </li>
        ) : (
          products.map((p) => (
            <li
              key={p.id}
              className="flex items-center justify-between rounded-card border border-surface-800 bg-surface-900 px-4 py-3"
            >
              <div>
                <span className="text-sm font-medium text-neutral-100">{p.name}</span>
                {p.category && (
                  <span className="ml-2 text-xs text-neutral-500">{p.category}</span>
                )}
              </div>
              <button
                onClick={() => makeAd(p.id)}
                disabled={busyAd !== null}
                className="rounded-md bg-surface-800 px-3 py-1.5 text-xs font-medium text-neutral-200 hover:bg-surface-700 disabled:opacity-40"
              >
                {busyAd === p.id ? "Generating…" : "Make ad"}
              </button>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
