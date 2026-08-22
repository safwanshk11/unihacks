import { useRef } from "react";
import type { Evaluation } from "../types/product";

/**
 * Field-level accuracy against a known-good Delivery Format file — the
 * metric the brief says judges look for.
 *
 * It reports the attainable ceiling alongside the raw score on purpose. A
 * bare "12%" invites the wrong conclusion; the ceiling shows how much of
 * the ground truth was ever reachable from the raw input at all.
 */
export function EvaluationPanel({
  evaluation,
  onEvaluate,
  busy,
}: {
  evaluation: Evaluation | null;
  onEvaluate: (file: File) => void;
  busy: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);

  return (
    <section className="mt-14">
      <div className="flex flex-wrap items-end justify-between gap-4 pb-5">
        <div>
          <h2 className="text-[22px] leading-none font-semibold tracking-[-0.03em]">Accuracy</h2>
          <p className="text-[13px] mt-2.5 max-w-[62ch] leading-[1.5]" style={{ color: "var(--ink-3)" }}>
            Score the enriched catalogue against a known-good Delivery Format file. Works with the 2-row worked example
            or the full 200-item ground truth, unchanged.
          </p>
        </div>
        <input
          ref={input}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onEvaluate(f);
            e.target.value = "";
          }}
        />
        <button
          onClick={() => input.current?.click()}
          disabled={busy}
          className="text-[13px] px-3.5 py-2 border transition-all disabled:opacity-45 whitespace-nowrap"
          style={{
            borderColor: "var(--rule)",
            backgroundColor: "var(--surface)",
            color: "var(--ink-2)",
            borderRadius: 7,
            boxShadow: "var(--shadow-sm)",
          }}
        >
          {busy ? "Scoring…" : evaluation ? "Score another file" : "Score against ground truth"}
        </button>
      </div>

      {!evaluation ? (
        <div
          className="surface px-6 py-8 text-[13px] leading-[1.6]"
          style={{ color: "var(--ink-3)" }}
        >
          No score yet. Upload a Delivery Format CSV and every field this pipeline populates is compared row by row,
          joined on part number.
        </div>
      ) : (
        <div className="surface overflow-hidden">
          <div className="cct-rule" />
          <div className="grid grid-cols-1 sm:grid-cols-3">
            {[
              { label: "Exact match", value: `${evaluation.overall.exact_pct}%`, sub: `${evaluation.overall.fields_compared} fields compared` },
              { label: "Allowing format drift", value: `${evaluation.overall.any_match_pct}%`, sub: "case & spacing normalised" },
              {
                label: "Reachable from input",
                value: `${evaluation.attainable_ceiling.reachable_pct}%`,
                sub: `${evaluation.attainable_ceiling.requires_manufacturer_source} of ${evaluation.attainable_ceiling.ground_truth_attributes} attributes need a manufacturer source`,
                signal: true,
              },
            ].map((c) => (
              <div key={c.label} className="px-5 py-5 border-r border-b sm:border-b-0 last:border-r-0" style={{ borderColor: "var(--rule-soft)" }}>
                <div
                  className="figure text-[30px] leading-none font-medium"
                  style={{ color: c.signal ? "var(--signal)" : "var(--ink)" }}
                >
                  {c.value}
                </div>
                <div className="eyebrow mt-3">{c.label}</div>
                <div className="text-[11px] mt-1.5 leading-[1.4]" style={{ color: "var(--ink-4)" }}>
                  {c.sub}
                </div>
              </div>
            ))}
          </div>

          <div className="px-5 py-3 border-t text-[12px] leading-[1.5]" style={{ borderColor: "var(--rule-soft)", color: "var(--ink-3)" }}>
            {evaluation.attainable_ceiling.note}
          </div>

          <table className="w-full border-collapse border-t" style={{ borderColor: "var(--rule)" }}>
            <thead>
              <tr style={{ backgroundColor: "var(--paper)" }}>
                <th className="eyebrow text-left font-normal py-3 px-5">Field</th>
                <th className="eyebrow text-left font-normal py-3 px-5 w-[92px]">Exact</th>
                <th className="eyebrow text-left font-normal py-3 px-5 w-[92px]">Any</th>
                <th className="eyebrow text-left font-normal py-3 px-5 w-[70px]">n</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(evaluation.by_field)
                .filter(([, v]) => v.compared > 0)
                .map(([name, v]) => (
                  <tr key={name} className="border-b last:border-b-0" style={{ borderColor: "var(--rule-soft)" }}>
                    <td className="py-3 px-5 text-[13px]">{name}</td>
                    <td
                      className="py-3 px-5 font-mono text-[12px]"
                      style={{ color: v.exact_pct > 0 ? "var(--ink)" : "var(--ink-4)" }}
                    >
                      {v.exact_pct}%
                    </td>
                    <td
                      className="py-3 px-5 font-mono text-[12px]"
                      style={{ color: v.any_match_pct > 0 ? "var(--ink)" : "var(--ink-4)" }}
                    >
                      {v.any_match_pct}%
                    </td>
                    <td className="py-3 px-5 font-mono text-[12px]" style={{ color: "var(--ink-4)" }}>
                      {v.compared}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
