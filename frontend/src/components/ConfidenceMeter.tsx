import type { Confidence } from "../types/product";

const LEVEL: Record<Confidence, number> = { low: 1, medium: 2, high: 3 };
const BAR_HEIGHTS = [4, 7, 10];

/**
 * Confidence as a light meter — three rising bars, lit to level.
 *
 * Deliberately monochrome: low confidence already surfaces in the Status
 * column, and amber is reserved for "needs a human." Encoding it twice
 * would spend the page's only color on redundant information.
 */
export function ConfidenceMeter({ confidence, label = true }: { confidence: Confidence; label?: boolean }) {
  const lit = LEVEL[confidence];
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap" title={`${confidence} confidence`}>
      <span className="inline-flex items-end gap-[2px]" aria-hidden style={{ height: 10 }}>
        {BAR_HEIGHTS.map((h, i) => (
          <span
            key={h}
            style={{
              width: 2,
              height: h,
              backgroundColor: i < lit ? "var(--ink)" : "var(--rule)",
            }}
          />
        ))}
      </span>
      {label && (
        <span className="text-[11px] capitalize" style={{ color: "var(--ink-3)" }}>
          {confidence}
        </span>
      )}
      <span className="sr-only">{confidence} confidence</span>
    </span>
  );
}
