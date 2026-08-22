import type { EnrichedProduct, Evaluation, Metrics, ProductPatch, RawProductIn, SortState } from "../types/product";

export type SeedInProgressDetail = { message: string; done: number; total: number };

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown, fallbackMessage: string) {
    const message =
      typeof detail === "string" ? detail : isSeedInProgressDetail(detail) ? detail.message : fallbackMessage;
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

export function isSeedInProgressDetail(detail: unknown): detail is SeedInProgressDetail {
  return (
    typeof detail === "object" &&
    detail !== null &&
    "done" in detail &&
    "total" in detail &&
    typeof (detail as SeedInProgressDetail).done === "number" &&
    typeof (detail as SeedInProgressDetail).total === "number"
  );
}

// Session token lives in sessionStorage, not localStorage: it should not
// outlive the browser tab for a console holding unpublished content.
const TOKEN_KEY = "lumen.session";
const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export const session = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (token: string) => sessionStorage.setItem(TOKEN_KEY, token),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

export function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const token = session.get();
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}/api${path}`, {
    ...init,
    headers: authHeaders({ "Content-Type": "application/json", ...(init?.headers as Record<string, string>) }),
  });
  if (!res.ok) {
    const body = await res.text();
    let detail: unknown;
    try {
      detail = (JSON.parse(body) as { detail?: unknown }).detail;
    } catch {
      // body wasn't JSON — ApiError falls back to the status text below
    }
    throw new ApiError(res.status, detail, `${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

export const api = {
  listProducts: () => request<EnrichedProduct[]>("/products"),
  getProduct: (id: number) => request<EnrichedProduct>(`/products/${id}`),
  createProduct: (raw: RawProductIn) =>
    request<EnrichedProduct>("/products", { method: "POST", body: JSON.stringify(raw) }),
  createProductsBatch: (raws: RawProductIn[]) =>
    request<EnrichedProduct[]>("/products/batch", { method: "POST", body: JSON.stringify(raws) }),
  seedProducts: () => request<EnrichedProduct[]>("/products/seed", { method: "POST" }),
  uploadCatalog: async (file: File) => {
    const body = new FormData();
    body.append("file", file);
    // No Content-Type header — the browser must set the multipart boundary.
    const res = await fetch(`${API_BASE}/api/products/upload`, { method: "POST", body, headers: authHeaders() });
    if (!res.ok) {
      const text = await res.text();
      let detail: unknown;
      try {
        detail = (JSON.parse(text) as { detail?: unknown }).detail;
      } catch {
        /* not JSON */
      }
      throw new ApiError(res.status, detail, `${res.status} ${res.statusText}: ${text}`);
    }
    return res.json() as Promise<{ imported: number; filename: string }>;
  },
  patchProduct: (id: number, patch: ProductPatch) =>
    request<EnrichedProduct>(`/products/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  downloadExport: async (format: "csv" | "json", sort?: SortState) => {
    const params = new URLSearchParams({ format });
    if (sort) {
      params.set("sort", sort.column);
      params.set("direction", sort.direction);
    }
    // Navigating the window would drop the Authorization header, so fetch
    // the file and hand the browser a blob instead.
    const res = await fetch(`${API_BASE}/api/products/export?${params.toString()}`, { headers: authHeaders() });
    if (!res.ok) throw new ApiError(res.status, undefined, `Export failed: ${res.status} ${res.statusText}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = format === "csv" ? "unilog_delivery_format.csv" : "lumen_export.json";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
  getMetrics: () => request<Metrics>("/metrics"),

  login: (username: string, password: string) =>
    request<{ token: string; username: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  me: () => request<{ username: string }>("/auth/me"),

  evaluate: async (file: File) => {
    const body = new FormData();
    body.append("file", file);
    const res = await fetch(`${API_BASE}/api/products/evaluate`, { method: "POST", body, headers: authHeaders() });
    if (!res.ok) {
      const text = await res.text();
      let detail: unknown;
      try {
        detail = (JSON.parse(text) as { detail?: unknown }).detail;
      } catch {
        /* not JSON */
      }
      throw new ApiError(res.status, detail, `${res.status} ${res.statusText}: ${text}`);
    }
    return res.json() as Promise<Evaluation>;
  },
};
