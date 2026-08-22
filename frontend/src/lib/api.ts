import type { EnrichedProduct, Metrics, ProductPatch, RawProductIn, SortState } from "../types/product";

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
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
  patchProduct: (id: number, patch: ProductPatch) =>
    request<EnrichedProduct>(`/products/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  exportUrl: (format: "csv" | "json", sort?: SortState) => {
    const params = new URLSearchParams({ format });
    if (sort) {
      params.set("sort", sort.column);
      params.set("direction", sort.direction);
    }
    return `/api/products/export?${params.toString()}`;
  },
  getMetrics: () => request<Metrics>("/metrics"),
};
