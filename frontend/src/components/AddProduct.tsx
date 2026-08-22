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

  const inputClass = "w-full border px-3 py-2 text-[13.5px] focus:outline-none";
  const inputStyle = { borderColor: "var(--rule)", backgroundColor: "var(--raised)", borderRadius: 3 };

  const ready = mfgPartNum.trim() && partDesc.trim() && partManuf.trim();

  return (
    <div className="max-w-[560px] mx-auto px-8 pb-24">
      <div className="pt-8 pb-6">
        <button
          onClick={onCancel}
          className="text-[13px] transition-colors hover:text-[color:var(--ink)]"
          style={{ color: "var(--ink-3)" }}
        >
          ← Catalog
        </button>
      </div>

      <div className="border-t pt-8" style={{ borderColor: "var(--rule)" }}>
        <h1 className="text-[26px] leading-[1.1] font-semibold tracking-[-0.03em]">Add a product</h1>
        <p className="text-[13px] mt-2.5 leading-[1.5]" style={{ color: "var(--ink-3)" }}>
          These are the four columns a distributor actually sends. Everything else on the record gets derived from them.
        </p>
      </div>

      <form
        className="flex flex-col gap-5 mt-9"
        onSubmit={(e) => {
          e.preventDefault();
          if (!ready) return;
          onSubmitSingle({
            mfg_part_num: mfgPartNum.trim(),
            part_desc: partDesc.trim(),
            part_manuf: partManuf.trim(),
            e1_brand: e1Brand.trim() || "-- Unbranded --",
          });
        }}
      >
        <label className="flex flex-col">
          <span className="eyebrow mb-2">Mfg_Part_Num</span>
          <input
            className={`${inputClass} font-mono text-[12.5px]`}
            style={inputStyle}
            placeholder="45573BK"
            value={mfgPartNum}
            onChange={(e) => setMfgPartNum(e.target.value)}
            required
          />
        </label>
        <label className="flex flex-col">
          <span className="eyebrow mb-2">Part_Desc</span>
          <input
            className={inputClass}
            style={inputStyle}
            placeholder="45573BK Kichler Wall Light"
            value={partDesc}
            onChange={(e) => setPartDesc(e.target.value)}
            required
          />
        </label>
        <label className="flex flex-col">
          <span className="eyebrow mb-2">Part_Manuf</span>
          <input
            className={inputClass}
            style={inputStyle}
            placeholder="Kichler Lighting (KICLI)"
            value={partManuf}
            onChange={(e) => setPartManuf(e.target.value)}
            required
          />
        </label>
        <label className="flex flex-col">
          <span className="eyebrow mb-2">
            E1_Brand <span style={{ textTransform: "none", letterSpacing: 0 }}>— optional</span>
          </span>
          <input
            className={inputClass}
            style={inputStyle}
            placeholder="Blank becomes '-- Unbranded --'"
            value={e1Brand}
            onChange={(e) => setE1Brand(e.target.value)}
          />
        </label>

        <button
          type="submit"
          disabled={submitting || !ready}
          className="self-start text-[13px] px-4 py-2 mt-2 transition-opacity disabled:opacity-40"
          style={{ backgroundColor: "var(--ink)", color: "var(--paper)", borderRadius: 3 }}
        >
          {submitting ? "Enriching…" : "Enrich product"}
        </button>
      </form>
    </div>
  );
}
