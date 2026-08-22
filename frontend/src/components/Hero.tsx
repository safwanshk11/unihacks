import type { EnrichedProduct, Metrics } from "../types/product";
import { ConfidenceMeter } from "./ConfidenceMeter";

/**
 * The thesis, stated with real data: one cryptic distributor string on the
 * left, the record it becomes on the right. This is the single most
 * characteristic thing in the subject's world, so it opens the page.
 *
 * The showcase record is chosen, not hardcoded — the richest item in the
 * catalog, so the transformation looks like what the pipeline actually does.
 */
function pickShowcase(products: EnrichedProduct[]): EnrichedProduct | null {
  if (products.length === 0) return null;
  return [...products].sort((a, b) => {
    const score = (p: EnrichedProduct) =>
      p.attributes.filter((x) => x.value && x.value !== "Not specified").length +
      (p.long_desc.source === "llm" ? 3 : 0);
    return score(b) - score(a);
  })[0];
}

export function Hero({ products, metrics }: { products: EnrichedProduct[]; metrics: Metrics | null }) {
  const item = pickShowcase(products);
  const fieldCount = item ? item.attributes.length + 7 : 0;

  return (
    <section className="pt-10 sm:pt-16 pb-10">
      <div className="max-w-[620px]">
        <span className="eyebrow rise rise-1">Industrial product intelligence</span>
        <h1 className="text-[30px] sm:text-[38px] lg:text-[42px] leading-[1.07] tracking-[-0.04em] font-semibold mt-4 rise rise-1">
          Cryptic part numbers,
          <br className="hidden sm:inline" /> made commerce-ready.
        </h1>
        <p className="text-[14.5px] leading-[1.6] mt-5 rise rise-2" style={{ color: "var(--ink-2)" }}>
          Deterministic rules read the structure a part number encodes. A local language model writes what rules
          can&rsquo;t. Every field carries where it came from and how sure it is.
        </p>
      </div>

      {item && (
        <div className="mt-11 grid grid-cols-1 md:grid-cols-[minmax(0,0.85fr)_auto_minmax(0,1.15fr)] items-stretch gap-4 md:gap-0 glow-in">
          {/* AS RECEIVED */}
          <div className="surface p-5 flex flex-col justify-between md:rounded-r-none md:border-r-0">
            <div className="eyebrow">As received</div>
            <div className="mt-5">
              <p className="font-mono text-[13px] leading-[1.5]" style={{ color: "var(--ink)" }}>
                {item.raw_part_desc}
              </p>
              <p className="text-[11.5px] mt-3" style={{ color: "var(--ink-4)" }}>
                {item.raw_part_manuf} · brand field empty
              </p>
            </div>
          </div>

          {/* The transformation — the spectrum runs left to right, warm to
              cool, the way a CCT scale is always printed. */}
          <div
            className="hidden md:flex items-center justify-center px-7"
            style={{
              backgroundColor: "var(--surface)",
              borderTop: "1px solid var(--rule)",
              borderBottom: "1px solid var(--rule)",
            }}
          >
            <div className="flex flex-col items-center gap-2.5">
              <span className="eyebrow" style={{ letterSpacing: "0.18em", color: "var(--ink-3)" }}>
                Lumen
              </span>
              <span className="flex items-center gap-1.5">
                <span className="cct-rule w-12 rounded-full" />
                <span style={{ color: "var(--k6500)", fontSize: 11, lineHeight: 1 }}>▶</span>
              </span>
            </div>
          </div>

          {/* ENRICHED — lit from above, because that's the whole idea */}
          <div
            className="surface p-5 md:rounded-l-none relative overflow-hidden"
            style={{
              boxShadow: "var(--shadow-md)",
              backgroundImage:
                "radial-gradient(120% 90% at 50% -20%, rgba(240,166,60,0.09) 0%, transparent 62%)",
            }}
          >
            <div className="flex items-center justify-between gap-4">
              <span className="eyebrow" style={{ color: "var(--signal)" }}>
                Enriched
              </span>
              <ConfidenceMeter confidence={item.classpath.confidence} size="sm" label={false} />
            </div>
            <p className="text-[15px] leading-[1.4] font-medium mt-4">{item.short_desc.value}</p>
            <p className="text-[12px] leading-[1.5] mt-2" style={{ color: "var(--ink-3)" }}>
              {item.classpath.value}
            </p>
            <div className="flex flex-wrap gap-1.5 mt-4">
              {item.attributes
                .filter((a) => a.value && a.value !== "Not specified")
                .slice(0, 5)
                .map((a) => (
                  <span
                    key={a.label}
                    className="text-[11px] px-2 py-[3px] rounded-full"
                    style={{ backgroundColor: "var(--paper)", border: "1px solid var(--rule-soft)", color: "var(--ink-2)" }}
                  >
                    {a.value}
                    {a.uom ? ` ${a.uom}` : ""}
                  </span>
                ))}
              <span className="text-[11px] px-2 py-[3px]" style={{ color: "var(--ink-4)" }}>
                +{Math.max(0, fieldCount - 5)} more fields
              </span>
            </div>
          </div>
        </div>
      )}

      {metrics && metrics.total > 0 && (
        <p className="text-[12.5px] mt-5 rise rise-3" style={{ color: "var(--ink-3)" }}>
          <span className="font-mono" style={{ color: "var(--ink)" }}>
            {metrics.llm?.long_desc_generated ?? 0}
          </span>{" "}
          descriptions written by{" "}
          <span className="font-mono text-[11.5px]" style={{ color: "var(--ink)" }}>
            {metrics.llm?.model}
          </span>
          , grounded strictly in extracted attributes — never invented.
        </p>
      )}
    </section>
  );
}
