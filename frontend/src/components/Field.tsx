import type { Confidence, EnrichedField, Source } from "../types/product";

/**
 * Provenance is encoded in ink weight, not hue — `llm` sits at full ink so
 * model-written fields stand out, while rule/input recede. That keeps the
 * page's only color (amber) exclusively for "needs a human."
 *
 * No meter icon here on purpose: the review page stacks a dozen of these
 * rows, and a dozen repeating signal-bar glyphs read as chrome. Confidence
 * still ships, as a word alongside the source tag. The meter stays on the
 * catalog table and hero, where it appears once per row and earns its space.
 */
const SOURCE_LABEL: Record<Source, string> = {
  input: "from input",
  inferred: "rule",
  llm: "llm",
};

const CONFIDENCE_INK: Record<Confidence, string> = {
  high: "var(--ink-3)",
  medium: "var(--ink-4)",
  low: "var(--signal)",
};

export function Field({
  label,
  field,
  editing,
  onChange,
  multiline = false,
  meta,
}: {
  label: string;
  field: EnrichedField;
  editing: boolean;
  onChange: (value: string) => void;
  multiline?: boolean;
  meta?: React.ReactNode;
}) {
  const inputStyle = {
    borderColor: "var(--rule)",
    color: "var(--ink)",
    backgroundColor: "var(--raised)",
    borderRadius: 3,
  };

  return (
    <div className="py-4 border-b" style={{ borderColor: "var(--rule-soft)" }}>
      <div className="flex items-center justify-between gap-4 mb-2">
        <span className="eyebrow">{label}</span>
        <span className="flex items-center gap-3 shrink-0">
          {meta}
          <span
            className="font-mono text-[10px] tracking-[0.04em] whitespace-nowrap"
            style={{ color: field.source === "llm" ? "var(--ink)" : "var(--ink-4)" }}
          >
            {SOURCE_LABEL[field.source]}
          </span>
          <span
            className="font-mono text-[10px] tracking-[0.04em] whitespace-nowrap"
            style={{ color: CONFIDENCE_INK[field.confidence] }}
            title={`${field.confidence} confidence`}
          >
            {field.confidence}
          </span>
        </span>
      </div>

      {editing ? (
        multiline ? (
          <textarea
            className="w-full border px-3 py-2 text-[13.5px] focus:outline-none"
            style={inputStyle}
            rows={3}
            value={field.value}
            onChange={(e) => onChange(e.target.value)}
          />
        ) : (
          <input
            className="w-full border px-3 py-2 text-[13.5px] focus:outline-none"
            style={inputStyle}
            value={field.value}
            onChange={(e) => onChange(e.target.value)}
          />
        )
      ) : (
        <p className="text-[14px] leading-[1.45]">{field.value}</p>
      )}

      <p className="text-[11.5px] mt-1.5 leading-[1.5]" style={{ color: "var(--ink-4)" }}>
        {field.rationale}
      </p>
    </div>
  );
}
