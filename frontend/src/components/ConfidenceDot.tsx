import type { Confidence } from "../types/product";

const COLOR: Record<Confidence, string> = {
  high: "var(--success)",
  medium: "var(--warning)",
  low: "var(--danger)",
};

export function ConfidenceDot({ confidence, label = true }: { confidence: Confidence; label?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className="inline-block h-1.5 w-1.5 rounded-full shrink-0"
        style={{ backgroundColor: COLOR[confidence] }}
        aria-hidden
      />
      {label && (
        <span className="text-xs font-medium capitalize" style={{ color: "var(--text-muted)" }}>
          {confidence}
        </span>
      )}
    </span>
  );
}
