export function Header({ onHome }: { onHome: () => void }) {
  return (
    <header
      className="sticky top-0 z-10 border-b backdrop-blur-sm"
      style={{ borderColor: "var(--border)", backgroundColor: "color-mix(in srgb, var(--bg) 85%, transparent)" }}
    >
      <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
        <button onClick={onHome} className="flex items-center gap-2.5">
          <span
            className="h-6 w-6 rounded-md flex items-center justify-center text-white text-xs font-bold"
            style={{ backgroundColor: "var(--accent)" }}
          >
            L
          </span>
          <span className="text-sm font-semibold tracking-tight">Lumen</span>
          <span className="text-sm hidden sm:inline" style={{ color: "var(--text-faint)" }}>
            Product Intelligence
          </span>
        </button>
        <span className="text-xs font-medium" style={{ color: "var(--text-faint)" }}>
          Real Unilog data · hybrid rules + local LLM
        </span>
      </div>
    </header>
  );
}
