import type { Confidence } from "../types/product";

const LEVEL: Record<Confidence, number> = { low: 1, medium: 2, high: 3 };
const BAR_HEIGHTS = [6, 10, 14];

/**
 * Confidence as a light meter — three rising bars, lit to level.
 *
 * Lit bars carry a faint warm bloom, so a high-confidence record literally
 * reads brighter than a low-confidence one. That's the whole conceit of the
 * page paying rent: in a lighting catalog, certainty looks like light.
 */
export function ConfidenceMeter({
  confidence,
  label = true,
  size = "md",
}: {
  confidence: Confidence;
  label?: boolean;
  size?: "sm" | "md";
}) {
  const lit = LEVEL[confidence];
  const scale = size === "sm" ? 0.7 : 1;

  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap" title={`${confidence} confidence`}>
      <span className="inline-flex items-end gap-[3px]" aria-hidden style={{ height: 14 * scale }}>
        {BAR_HEIGHTS.map((h, i) => {
          const on = i < lit;
          return (
            <span
              key={h}
              style={{
                width: 3 * scale,
                height: h * scale,
                borderRadius: 1,
                backgroundColor: on ? "var(--ink)" : "var(--rule)",
                boxShadow: on && i === lit - 1 ? "0 0 6px rgba(240,166,60,0.55)" : undefined,
              }}
            />
          );
        })}
      </span>
      {label && (
        <span className="text-[11.5px] capitalize" style={{ color: "var(--ink-3)" }}>
          {confidence}
        </span>
      )}
      <span className="sr-only">{confidence} confidence</span>
    </span>
  );
}
