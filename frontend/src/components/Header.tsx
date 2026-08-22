export function Header({ onHome, model }: { onHome: () => void; model?: string }) {
  return (
    <header
      className="sticky top-0 z-20 border-b backdrop-blur-md"
      style={{ borderColor: "var(--rule)", backgroundColor: "color-mix(in srgb, var(--paper) 88%, transparent)" }}
    >
      <div className="max-w-[1080px] mx-auto px-8 h-[52px] flex items-center justify-between gap-6">
        <button onClick={onHome} className="flex items-baseline gap-2.5 group">
          <span className="text-[15px] font-semibold tracking-[-0.02em]">Lumen</span>
          <span className="eyebrow hidden sm:inline">Product intelligence</span>
        </button>
        {model && (
          <span className="eyebrow truncate" title={`Enrichment: deterministic rules + ${model}`}>
            rules + {model}
          </span>
        )}
      </div>
    </header>
  );
}
