import { useMemo, useRef, useState } from "react";
import type { Confidence, EnrichedProduct, Evaluation, Metrics, SortColumn, SortState } from "../types/product";
import { ConfidenceMeter } from "./ConfidenceMeter";
import { EvaluationPanel } from "./EvaluationPanel";
import { Hero } from "./Hero";
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

function Readout({ metrics }: { metrics: Metrics | null }) {
  if (!metrics || metrics.total === 0) return null;

  const queue = metrics.needs_review ?? 0;
  const cells: { label: string; value: string; sub?: string; signal?: boolean }[] = [
    { label: "Records", value: String(metrics.total), sub: "enriched end to end" },
    {
      label: "Auto-approved",
      value: String(metrics.review_status?.auto_approved ?? 0),
      sub: `${metrics.review_status?.auto_approved_pct ?? 0}% cleared without a human`,
    },
    { label: "Needs review", value: String(queue), sub: "flagged or low confidence", signal: queue > 0 },
    { label: "From input", value: `${metrics.attributes?.from_input_pct ?? 0}%`, sub: "read, not inferred" },
    { label: "In vocabulary", value: `${metrics.lov_compliance?.compliant_pct ?? 0}%`, sub: "values inside the LOV" },
    {
      label: "Within limits",
      value: `${metrics.char_limit_compliance?.invoice_desc_ok_pct ?? 0}%`,
      sub: "invoice desc ≤ 40 char",
    },
  ];

  const unreachable = metrics.llm?.llm_unreachable_count ?? 0;

  return (
    <div className="surface overflow-hidden rise rise-3" style={{ boxShadow: "var(--shadow-sm)" }}>
      <div className="cct-rule" />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
        {cells.map((c) => (
          <div
            key={c.label}
            className="px-5 py-5 border-r border-b lg:border-b-0 last:border-r-0"
            style={{ borderColor: "var(--rule-soft)" }}
          >
            <div
              className="figure text-[30px] leading-none font-medium"
              style={{
                color: c.signal ? "var(--signal)" : "var(--ink)",
                textShadow: c.signal ? "0 0 18px rgba(229,137,26,0.28)" : undefined,
              }}
            >
              {c.value}
            </div>
            <div className="eyebrow mt-3">{c.label}</div>
            {c.sub && (
              <div className="text-[11px] mt-1.5 leading-[1.4]" style={{ color: "var(--ink-4)" }}>
                {c.sub}
              </div>
            )}
          </div>
        ))}
      </div>
      {unreachable > 0 && (
        <div
          className="px-5 py-2.5 border-t text-[12px]"
          style={{ borderColor: "var(--rule-soft)", backgroundColor: "var(--signal-wash)", color: "var(--signal)" }}
        >
          {unreachable} record{unreachable === 1 ? "" : "s"} fell back to rules — {metrics.llm?.backend} unreachable
        </div>
      )}
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
    <th className={`text-left font-normal py-3.5 px-5 ${className}`}>
      <button
        onClick={() => onSort(column)}
        className="eyebrow inline-flex items-center gap-1.5 transition-colors hover:text-[color:var(--ink-2)]"
        style={{ color: active ? "var(--ink)" : undefined }}
      >
        {label}
        <span aria-hidden style={{ opacity: active ? 1 : 0, fontSize: 7 }}>
          {sort?.direction === "asc" ? "▲" : "▼"}
        </span>
      </button>
    </th>
  );
}

function ActionButton({
  children,
  onClick,
  disabled,
  title,
  primary,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  title?: string;
  primary?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className="text-[13px] px-3.5 py-2 border transition-all disabled:opacity-45 whitespace-nowrap"
      style={
        primary
          ? {
              borderColor: "var(--ink)",
              backgroundColor: "var(--ink)",
              color: "var(--paper-lit)",
              borderRadius: 7,
              boxShadow: "var(--shadow-sm)",
            }
          : {
              borderColor: "var(--rule)",
              backgroundColor: "var(--surface)",
              color: "var(--ink-2)",
              borderRadius: 7,
              boxShadow: "var(--shadow-sm)",
            }
      }
    >
      {children}
    </button>
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
  onImport,
  onEvaluate,
  evaluation,
}: {
  products: EnrichedProduct[];
  metrics: Metrics | null;
  loading: boolean;
  seeding: boolean;
  onOpen: (id: number) => void;
  onSeed: () => void;
  onAdd: () => void;
  onExport: (format: "csv" | "json", sort: SortState) => void;
  onImport: (file: File) => void;
  onEvaluate: (file: File) => void;
  evaluation: Evaluation | null;
}) {
  const [sort, setSort] = useState<SortState>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const toggleSort = (column: SortColumn) => {
    setSort((prev) => {
      if (prev?.column !== column) return { column, direction: "asc" };
      return { column, direction: prev.direction === "asc" ? "desc" : "asc" };
    });
  };

  const sortedProducts = useMemo(() => sortProducts(products, sort), [products, sort]);
  const needsReview = products.filter((p) => p.status === "pending").length;

  return (
    <div className="max-w-[1120px] mx-auto px-8 pb-28">
      <Hero products={products} metrics={metrics} />

      <div className="mt-2">
        <Readout metrics={metrics} />
      </div>

      <div className="pt-14 pb-5 flex flex-wrap items-end justify-between gap-5">
        <div>
          <h2 className="text-[22px] leading-none font-semibold tracking-[-0.03em]">Catalog</h2>
          <p className="text-[13px] mt-2.5" style={{ color: "var(--ink-3)" }}>
            {products.length} record{products.length === 1 ? "" : "s"}
            {needsReview > 0 && (
              <>
                {" · "}
                <span style={{ color: "var(--signal)" }}>{needsReview} waiting on you</span>
              </>
            )}
          </p>
        </div>
        <div className="flex gap-2.5">
          <input
            ref={fileInput}
            type="file"
            accept=".csv,.xlsx,.xlsm"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onImport(f);
              e.target.value = "";
            }}
          />
          <ActionButton
            onClick={() => fileInput.current?.click()}
            disabled={seeding}
            title="Enrich your own catalogue (.csv or .xlsx)"
          >
            Import file
          </ActionButton>
          <ActionButton onClick={onAdd} disabled={seeding}>
            Add product
          </ActionButton>
          <ActionButton onClick={onSeed} disabled={seeding}>
            {seeding ? `Enriching ${products.length}/211…` : "Reseed"}
          </ActionButton>
          <ActionButton
            onClick={() => onExport("csv", sort)}
            disabled={seeding}
            primary
            title={sort ? `Exports sorted by ${sort.column} (${sort.direction})` : "Exports in default order"}
          >
            Export CSV
          </ActionButton>
        </div>
      </div>

      <div className="surface overflow-hidden">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b" style={{ backgroundColor: "var(--paper)", borderColor: "var(--rule)" }}>
              <th className="eyebrow text-left font-normal py-3.5 px-5 w-[136px] hidden md:table-cell">MPN</th>
              <th className="eyebrow text-left font-normal py-3.5 px-5">Product</th>
              <SortableHeader
                label="Class"
                column="classpath"
                sort={sort}
                onSort={toggleSort}
                className="w-[186px] hidden lg:table-cell"
              />
              <SortableHeader
                label="Confidence"
                column="confidence"
                sort={sort}
                onSort={toggleSort}
                className="w-[136px] hidden sm:table-cell"
              />
              <SortableHeader label="Status" column="status" sort={sort} onSort={toggleSort} className="w-[152px]" />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} className="py-16 text-center text-[13px]" style={{ color: "var(--ink-3)" }}>
                  Loading catalog…
                </td>
              </tr>
            )}
            {!loading && products.length === 0 && (
              <tr>
                <td colSpan={5} className="py-20 text-center">
                  <p className="text-[15px]">Nothing enriched yet.</p>
                  <p className="text-[13px] mt-1.5" style={{ color: "var(--ink-3)" }}>
                    Reseed to load 211 real lighting rows, or add a single product.
                  </p>
                </td>
              </tr>
            )}
            {sortedProducts.map((p) => (
              <tr
                key={p.id}
                onClick={() => onOpen(p.id)}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onOpen(p.id);
                  }
                }}
                className="group cursor-pointer border-b last:border-b-0 transition-colors hover:bg-[color:var(--paper)]"
                style={{ borderColor: "var(--rule-soft)" }}
              >
                <td
                  className="py-4 px-5 font-mono text-[11px] align-middle transition-colors hidden md:table-cell"
                  style={{ color: "var(--ink-4)" }}
                >
                  <span className="group-hover:text-[color:var(--ink-2)]">{p.raw_mfg_part_num}</span>
                </td>
                <td className="py-4 px-5 text-[13.5px] align-middle" style={{ color: "var(--ink)" }}>
                  {p.short_desc.value}
                  <span className="block md:hidden font-mono text-[10.5px] mt-1" style={{ color: "var(--ink-4)" }}>
                    {p.raw_mfg_part_num} · {classpathLeaf(p)}
                  </span>
                </td>
                <td
                  className="py-4 px-5 text-[12.5px] align-middle hidden lg:table-cell"
                  style={{ color: "var(--ink-3)" }}
                >
                  {classpathLeaf(p)}
                </td>
                <td className="py-4 px-5 align-middle hidden sm:table-cell">
                  <ConfidenceMeter confidence={overallConfidence(p)} />
                </td>
                <td className="py-4 px-5 align-middle">
                  <StampBadge status={p.status} autoApproved={isAutoApproved(p)} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <EvaluationPanel evaluation={evaluation} onEvaluate={onEvaluate} busy={seeding} />
    </div>
  );
}
