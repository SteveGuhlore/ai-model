import type { Content, GenerateResult, Job, Persona, Product } from "./types";

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

  // Generation + training are async: they return a job id; poll getJob/pollJob.
  generate: (body: Record<string, unknown>) =>
    req<{ job_id: string; status: string }>("/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  generateProductAd: (body: Record<string, unknown>) =>
    req<{ job_id: string; status: string }>("/generate/product-ad", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getJob: <T = unknown>(id: string) => req<Job<T>>(`/jobs/${id}`),

  async pollJob<T = unknown>(
    id: string,
    { intervalMs = 1500, timeoutMs = 600000 }: { intervalMs?: number; timeoutMs?: number } = {},
  ): Promise<T> {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const job = await req<Job<T>>(`/jobs/${id}`);
      if (job.status === "succeeded") return job.result as T;
      if (job.status === "failed") throw new Error(job.error || "job failed");
      await new Promise((r) => setTimeout(r, intervalMs));
    }
    throw new Error("job timed out");
  },

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
