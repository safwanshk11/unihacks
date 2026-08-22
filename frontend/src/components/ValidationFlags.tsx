import type { ValidationFlag } from "../types/product";

const STYLE: Record<ValidationFlag["severity"], { bg: string; fg: string }> = {
  error: { bg: "var(--danger-soft)", fg: "var(--danger)" },
  warning: { bg: "var(--warning-soft)", fg: "var(--warning)" },
  info: { bg: "var(--info-soft)", fg: "var(--info)" },
};

export function ValidationFlags({ flags }: { flags: ValidationFlag[] }) {
  if (flags.length === 0) {
    return (
      <div
        className="rounded-lg px-3.5 py-2.5 text-sm"
        style={{ backgroundColor: "var(--success-soft)", color: "var(--success)" }}
      >
        No issues found — clean pass.
      </div>
    );
  }

  return (
    <ul className="flex flex-col gap-1.5">
      {flags.map((flag, i) => {
        const s = STYLE[flag.severity];
        return (
          <li
            key={i}
            className="flex items-start gap-2.5 rounded-lg px-3.5 py-2.5 text-sm"
            style={{ backgroundColor: s.bg, color: s.fg }}
          >
            <span className="h-1.5 w-1.5 rounded-full mt-1.5 shrink-0" style={{ backgroundColor: s.fg }} />
            <span>
              <span className="font-medium mr-1.5">{flag.field}</span>
              {flag.issue}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
