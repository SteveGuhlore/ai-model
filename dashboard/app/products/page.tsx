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

  async function load() {
    setProducts(await api.listProducts());
    setPersonas(await api.listPersonas());
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
    const persona = personas.find((p) => p.status === "ready") || personas[0];
    if (!persona) {
      setError("Create and train a persona first.");
      return;
    }
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
                className="rounded-md bg-surface-800 px-3 py-1.5 text-xs font-medium text-neutral-200 hover:bg-surface-700"
              >
                Make ad
              </button>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
