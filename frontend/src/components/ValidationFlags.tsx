import type { ValidationFlag } from "../types/product";

/**
 * Only warning/error carry the signal color. Info flags (including the
 * auto-approval note) stay grayscale — they're a record of what happened,
 * not a request for attention.
 */
export function ValidationFlags({ flags }: { flags: ValidationFlag[] }) {
  if (flags.length === 0) {
    return (
      <p className="text-[13px]" style={{ color: "var(--ink-3)" }}>
        No issues found.
      </p>
    );
  }

  return (
    <ul className="flex flex-col">
      {flags.map((flag, i) => {
        const isSignal = flag.severity === "warning" || flag.severity === "error";
        return (
          <li
            key={i}
            className="flex items-start gap-3 py-2.5 border-b last:border-b-0"
            style={{ borderColor: "var(--rule-soft)" }}
          >
            <span
              className="mt-[7px] h-[5px] w-[5px] rounded-full shrink-0"
              style={
                isSignal
                  ? { backgroundColor: "var(--signal-mark)" }
                  : { border: "1px solid var(--ink-4)" }
              }
              aria-hidden
            />
            <span className="text-[13px] leading-[1.5]" style={{ color: isSignal ? "var(--ink)" : "var(--ink-3)" }}>
              <span className="font-mono text-[10.5px] tracking-[0.04em] mr-2" style={{ color: "var(--ink-4)" }}>
                {flag.field}
              </span>
              {flag.issue}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
