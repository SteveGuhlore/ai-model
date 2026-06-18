import type { Content, Persona, Product } from "./types";

// All calls go through the Next proxy (/api -> FastAPI). No secrets client-side.
const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listPersonas: () => req<Persona[]>("/personas"),
  createPersona: (body: Partial<Persona>) =>
    req<Persona>("/personas", { method: "POST", body: JSON.stringify(body) }),
  trainPersona: (id: string, images_zip_url: string) =>
    req<Persona>(`/personas/${id}/train`, {
      method: "POST",
      body: JSON.stringify({ images_zip_url }),
    }),

  listProducts: () => req<Product[]>("/products").catch(() => [] as Product[]),
  createProduct: (body: Partial<Product>) =>
    req<Product>("/products", { method: "POST", body: JSON.stringify(body) }),

  generate: (body: Record<string, unknown>) =>
    req<{ created: number; content: Content[] }>("/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  generateProductAd: (body: Record<string, unknown>) =>
    req<{ created: number; content: Content[] }>("/generate/product-ad", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listContent: (params: { persona_id?: string; review_status?: string } = {}) => {
    const q = new URLSearchParams(params as Record<string, string>).toString();
    return req<Content[]>(`/content${q ? `?${q}` : ""}`);
  },
  review: (id: string, status: "approved" | "rejected") =>
    req<{ id: string; review_status: string }>(`/content/${id}/review`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),
};
