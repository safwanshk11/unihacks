import { useMemo, useState } from "react";
import type { Confidence, EnrichedProduct, Metrics, SortColumn, SortState } from "../types/product";
import { ConfidenceDot } from "./ConfidenceDot";
import { StampBadge } from "./StampBadge";

const CONFIDENCE_RANK: Record<Confidence, number> = { low: 0, medium: 1, high: 2 };
const STATUS_RANK: Record<EnrichedProduct["status"], number> = { pending: 0, reviewed: 1 };

function overallConfidence(p: EnrichedProduct): Confidence {
  const all = [p.classpath, ...p.attributes];
  return all.reduce(
    (worst, f) => (CONFIDENCE_RANK[f.confidence] < CONFIDENCE_RANK[worst] ? f.confidence : worst),
    "high" as Confidence,
  );
}

function classpathLeaf(p: EnrichedProduct): string {
  return p.classpath.value.split(">").pop()?.trim() ?? p.classpath.value;
}

function isAutoApproved(p: EnrichedProduct): boolean {
  return p.validation_flags.some((f) => f.field === "status");
}

function sortProducts(products: EnrichedProduct[], sort: SortState): EnrichedProduct[] {
  if (!sort) return products;
  const dir = sort.direction === "asc" ? 1 : -1;
  return [...products].sort((a, b) => {
    switch (sort.column) {
      case "classpath":
        return dir * classpathLeaf(a).localeCompare(classpathLeaf(b));
      case "confidence":
        return dir * (CONFIDENCE_RANK[overallConfidence(a)] - CONFIDENCE_RANK[overallConfidence(b)]);
      case "status":
        return dir * (STATUS_RANK[a.status] - STATUS_RANK[b.status]);
    }
  });
}

function MetricsPanel({ metrics }: { metrics: Metrics | null }) {
  if (!metrics || metrics.total === 0) return null;
  const cells = [
    { label: "Classified (high conf.)", value: `${metrics.classification_confidence?.high ?? 0}/${metrics.total}` },
    { label: "Attributes from input", value: `${metrics.attributes?.from_input_pct ?? 0}%` },
    { label: "Placeholder LOV compliance", value: `${metrics.lov_compliance?.compliant_pct ?? 0}%` },
    { label: "Invoice desc ≤ 40 char", value: `${metrics.char_limit_compliance?.invoice_desc_ok_pct ?? 0}%` },
    { label: "Mobile desc in 60-80 char", value: `${metrics.char_limit_compliance?.mobile_desc_ok_pct ?? 0}%` },
    {
      label: "Auto-approved",
      value: `${metrics.review_status?.auto_approved ?? 0} (${metrics.review_status?.auto_approved_pct ?? 0}%)`,
    },
    { label: "Needs review", value: `${metrics.needs_review ?? 0} (${metrics.needs_review_pct ?? 0}%)` },
  ];
  const unreachable = metrics.llm?.llm_unreachable_count ?? 0;

  return (
    <div
      className="rounded-xl border p-5 mb-6"
      style={{ borderColor: "var(--border)", backgroundColor: "var(--surface)" }}
    >
      <div
        className="flex items-center justify-between rounded-lg px-3.5 py-2.5 mb-4"
        style={{ backgroundColor: "var(--ai-soft)" }}
      >
        <span className="text-sm font-medium" style={{ color: "var(--ai)" }}>
          {metrics.llm?.long_desc_generated ?? 0}/{metrics.total} descriptions written by {metrics.llm?.model ?? "an LLM"}
          {metrics.llm?.backend && ` (${metrics.llm.backend})`}
          {(metrics.llm?.fallback_classifications ?? 0) > 0 &&
            ` · ${metrics.llm?.fallback_classifications} ambiguous items reclassified by the LLM`}
        </span>
        {unreachable > 0 && (
          <span className="text-xs font-medium" style={{ color: "var(--warning)" }}>
            {metrics.llm?.backend ?? "LLM"} unreachable for {unreachable} item{unreachable === 1 ? "" : "s"} — rule-based fallback used
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        {cells.map((c) => (
          <div key={c.label}>
            <div className="text-lg font-semibold tracking-tight">{c.value}</div>
            <div className="text-xs mt-0.5" style={{ color: "var(--text-faint)" }}>
              {c.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function SortableHeader({
  label,
  column,
  sort,
  onSort,
  className = "",
}: {
  label: string;
  column: SortColumn;
  sort: SortState;
  onSort: (column: SortColumn) => void;
  className?: string;
}) {
  const active = sort?.column === column;
  return (
    <th className={`px-4 py-2.5 text-xs font-medium select-none ${className}`} style={{ color: "var(--text-faint)" }}>
      <button
        onClick={() => onSort(column)}
        className="flex items-center gap-1 hover:text-inherit"
        style={{ color: active ? "var(--text)" : "var(--text-faint)" }}
      >
        {label}
        <span className="text-[10px] w-2.5 inline-block" style={{ color: active ? "var(--accent)" : "transparent" }}>
          {active && sort?.direction === "asc" ? "▲" : "▼"}
        </span>
      </button>
    </th>
  );
}

export function CatalogDashboard({
  products,
  metrics,
  loading,
  seeding,
  onOpen,
  onSeed,
  onAdd,
  onExport,
}: {
  products: EnrichedProduct[];
  metrics: Metrics | null;
  loading: boolean;
  seeding: boolean;
  onOpen: (id: number) => void;
  onSeed: () => void;
  onAdd: () => void;
  onExport: (format: "csv" | "json", sort: SortState) => void;
}) {
  const [sort, setSort] = useState<SortState>(null);

  const toggleSort = (column: SortColumn) => {
    setSort((prev) => {
      if (prev?.column !== column) return { column, direction: "asc" };
      return { column, direction: prev.direction === "asc" ? "desc" : "asc" };
    });
  };

  const sortedProducts = useMemo(() => sortProducts(products, sort), [products, sort]);

  const flaggedCount = products.filter((p) =>
    p.validation_flags.some((f) => f.severity === "warning" || f.severity === "error"),
  ).length;

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Lighting Catalog</h1>
          <p className="text-sm mt-0.5" style={{ color: "var(--text-muted)" }}>
            {products.length} item{products.length === 1 ? "" : "s"} on file
            {flaggedCount > 0 && (
              <>
                {" "}
                · <span style={{ color: "var(--warning)" }}>{flaggedCount} flagged for review</span>
              </>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onAdd}
            disabled={seeding}
            className="text-sm font-medium px-3.5 py-2 rounded-lg border hover:bg-black/[0.02] transition-colors disabled:opacity-50"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}
          >
            Add product
          </button>
          <button
            onClick={onSeed}
            disabled={seeding}
            className="text-sm font-medium px-3.5 py-2 rounded-lg border hover:bg-black/[0.02] transition-colors disabled:opacity-70"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}
          >
            {seeding ? `Enriching with local LLM… ${products.length}/211` : "Reseed from real data"}
          </button>
          <button
            onClick={() => onExport("csv", sort)}
            disabled={seeding}
            className="text-sm font-medium px-3.5 py-2 rounded-lg text-white transition-colors disabled:opacity-50"
            style={{ backgroundColor: "var(--accent)" }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "var(--accent-hover)")}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "var(--accent)")}
            title={sort ? `Exports sorted by ${sort.column} (${sort.direction})` : "Exports in default order"}
          >
            Export CSV
          </button>
        </div>
      </div>

      <MetricsPanel metrics={metrics} />

      <div
        className="rounded-xl overflow-hidden border"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--surface)" }}
      >
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b" style={{ borderColor: "var(--border)" }}>
              <th className="px-4 py-2.5 w-28 text-xs font-medium" style={{ color: "var(--text-faint)" }}>
                MPN
              </th>
              <th className="px-4 py-2.5 text-xs font-medium" style={{ color: "var(--text-faint)" }}>
                Title
              </th>
              <SortableHeader label="Classpath" column="classpath" sort={sort} onSort={toggleSort} className="w-52" />
              <SortableHeader label="Confidence" column="confidence" sort={sort} onSort={toggleSort} className="w-32" />
              <SortableHeader label="Status" column="status" sort={sort} onSort={toggleSort} className="w-28" />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-sm" style={{ color: "var(--text-muted)" }}>
                  Loading catalog…
                </td>
              </tr>
            )}
            {!loading && products.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-14 text-center text-sm" style={{ color: "var(--text-muted)" }}>
                  Nothing here yet. Reseed from the real data or add a product to get started.
                </td>
              </tr>
            )}
            {sortedProducts.map((p) => (
              <tr
                key={p.id}
                onClick={() => onOpen(p.id)}
                className="cursor-pointer border-b last:border-b-0 hover:bg-black/[0.015] transition-colors"
                style={{ borderColor: "var(--border-soft)" }}
              >
                <td className="px-4 py-3 font-mono text-xs" style={{ color: "var(--text-faint)" }}>
                  {p.raw_mfg_part_num}
                </td>
                <td className="px-4 py-3 font-medium">{p.short_desc.value}</td>
                <td className="px-4 py-3">
                  <span
                    className="text-xs px-2 py-1 rounded-md"
                    style={{ backgroundColor: "var(--bg)", color: "var(--text-muted)" }}
                  >
                    {classpathLeaf(p)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <ConfidenceDot confidence={overallConfidence(p)} />
                </td>
                <td className="px-4 py-3">
                  <StampBadge status={p.status} autoApproved={isAutoApproved(p)} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
