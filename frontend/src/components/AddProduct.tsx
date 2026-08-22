import { useState } from "react";
import type { RawProductIn } from "../types/product";

export function AddProduct({
  onSubmitSingle,
  onCancel,
  submitting,
}: {
  onSubmitSingle: (raw: RawProductIn) => void;
  onCancel: () => void;
  submitting: boolean;
}) {
  const [mfgPartNum, setMfgPartNum] = useState("");
  const [partDesc, setPartDesc] = useState("");
  const [partManuf, setPartManuf] = useState("");
  const [e1Brand, setE1Brand] = useState("");

  const inputClass = "w-full rounded-lg border px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2";
  const inputStyle = { borderColor: "var(--border)" };
  const labelClass = "text-xs font-medium mb-1.5";
  const labelStyle = { color: "var(--text-muted)" };

  return (
    <div className="max-w-xl mx-auto px-6 py-10">
      <button
        onClick={onCancel}
        className="text-sm font-medium mb-5 flex items-center gap-1"
        style={{ color: "var(--text-muted)" }}
      >
        ← Back to catalog
      </button>
      <h1 className="text-xl font-semibold tracking-tight mb-1">Add product</h1>
      <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
        Raw catalog row — same 4 fields as Unilog's real input schema.
      </p>

      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (!mfgPartNum.trim() || !partDesc.trim() || !partManuf.trim()) return;
          onSubmitSingle({
            mfg_part_num: mfgPartNum.trim(),
            part_desc: partDesc.trim(),
            part_manuf: partManuf.trim(),
            e1_brand: e1Brand.trim() || "-- Unbranded --",
          });
        }}
      >
        <label className="flex flex-col">
          <span className={labelClass} style={labelStyle}>
            Mfg Part Num *
          </span>
          <input
            className={`${inputClass} font-mono`}
            style={inputStyle}
            placeholder="e.g. 45573BK"
            value={mfgPartNum}
            onChange={(e) => setMfgPartNum(e.target.value)}
            required
          />
        </label>
        <label className="flex flex-col">
          <span className={labelClass} style={labelStyle}>
            Part Desc *
          </span>
          <input
            className={inputClass}
            style={inputStyle}
            placeholder="e.g. 45573BK Kichler Wall Light"
            value={partDesc}
            onChange={(e) => setPartDesc(e.target.value)}
            required
          />
        </label>
        <label className="flex flex-col">
          <span className={labelClass} style={labelStyle}>
            Part Manuf *
          </span>
          <input
            className={inputClass}
            style={inputStyle}
            placeholder="e.g. Kichler Lighting (KICLI)"
            value={partManuf}
            onChange={(e) => setPartManuf(e.target.value)}
            required
          />
        </label>
        <label className="flex flex-col">
          <span className={labelClass} style={labelStyle}>
            E1 Brand (optional)
          </span>
          <input
            className={inputClass}
            style={inputStyle}
            placeholder="Leave blank for '-- Unbranded --'"
            value={e1Brand}
            onChange={(e) => setE1Brand(e.target.value)}
          />
        </label>
        <button
          type="submit"
          disabled={submitting || !mfgPartNum.trim() || !partDesc.trim() || !partManuf.trim()}
          className="self-start text-sm font-medium px-4 py-2.5 rounded-lg text-white disabled:opacity-50"
          style={{ backgroundColor: "var(--accent)" }}
        >
          {submitting ? "Enriching…" : "Enrich product"}
        </button>
      </form>
    </div>
  );
}
