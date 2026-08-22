import type { EnrichedField, Source } from "../types/product";
import { ConfidenceDot } from "./ConfidenceDot";

const SOURCE_STYLE: Record<Source, { bg: string; fg: string; label: string }> = {
  input: { bg: "var(--info-soft)", fg: "var(--info)", label: "From input" },
  inferred: { bg: "var(--bg)", fg: "var(--text-muted)", label: "Rule-based" },
  llm: { bg: "var(--ai-soft)", fg: "var(--ai)", label: "AI generated" },
};

export function Field({
  label,
  field,
  editing,
  onChange,
  multiline = false,
}: {
  label: string;
  field: EnrichedField;
  editing: boolean;
  onChange: (value: string) => void;
  multiline?: boolean;
}) {
  return (
    <div className="py-3 border-b" style={{ borderColor: "var(--border-soft)" }}>
      <div className="flex items-center justify-between gap-3 mb-1.5">
        <span className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
          {label}
        </span>
        <div className="flex items-center gap-2 shrink-0">
          <ConfidenceDot confidence={field.confidence} />
          <span
            className="text-[11px] font-medium px-1.5 py-0.5 rounded"
            style={{ backgroundColor: SOURCE_STYLE[field.source].bg, color: SOURCE_STYLE[field.source].fg }}
          >
            {SOURCE_STYLE[field.source].label}
          </span>
        </div>
      </div>

      {editing ? (
        multiline ? (
          <textarea
            className="w-full rounded-md border px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}
            rows={3}
            value={field.value}
            onChange={(e) => onChange(e.target.value)}
          />
        ) : (
          <input
            className="w-full rounded-md border px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}
            value={field.value}
            onChange={(e) => onChange(e.target.value)}
          />
        )
      ) : (
        <p className="text-sm leading-snug">{field.value}</p>
      )}
      <p className="text-xs mt-1" style={{ color: "var(--text-faint)" }}>
        {field.rationale}
      </p>
    </div>
  );
}
