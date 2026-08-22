import { useEffect, useState } from "react";
import type { EnrichedProduct, ProductPatch } from "../types/product";
import { Field } from "./Field";
import { StampBadge } from "./StampBadge";
import { ValidationFlags } from "./ValidationFlags";

type Draft = {
  manufacturer_name: string;
  brand_name: string;
  classpath: string;
  invoice_desc: string;
  mobile_desc: string;
  short_desc: string;
  long_desc: string;
  attributes: Record<string, string>;
};

function draftFrom(p: EnrichedProduct): Draft {
  return {
    manufacturer_name: p.manufacturer_name.value,
    brand_name: p.brand_name.value,
    classpath: p.classpath.value,
    invoice_desc: p.invoice_desc.value,
    mobile_desc: p.mobile_desc.value,
    short_desc: p.short_desc.value,
    long_desc: p.long_desc.value,
    attributes: Object.fromEntries(p.attributes.map((a) => [a.label, a.value])),
  };
}

function CharCount({ value, min, max }: { value: string; min?: number; max?: number }) {
  const len = value.length;
  const ok = (min === undefined || len >= min) && (max === undefined || len <= max);
  const target = min !== undefined && max !== undefined ? `${min}–${max}` : `≤${max}`;
  return (
    <span
      className="font-mono text-[10px] tracking-[0.04em] whitespace-nowrap"
      style={{ color: ok ? "var(--ink-4)" : "var(--signal)" }}
      title={`Target ${target} characters`}
    >
      {len}/{target}
    </span>
  );
}

function RawField({ label, value }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="mb-5">
      <div className="eyebrow mb-1.5">{label}</div>
      <p className="text-[13.5px] leading-[1.45]" style={{ color: "var(--ink-2)" }}>
        {value}
      </p>
    </div>
  );
}

export function ProductReview({
  product,
  onBack,
  onSave,
  saving,
}: {
  product: EnrichedProduct;
  onBack: () => void;
  onSave: (id: number, patch: ProductPatch) => Promise<void>;
  saving: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Draft>(() => draftFrom(product));

  useEffect(() => {
    setDraft(draftFrom(product));
    setEditing(false);
  }, [product]);

  const handleSaveEdits = async () => {
    await onSave(product.id, {
      manufacturer_name: draft.manufacturer_name,
      brand_name: draft.brand_name,
      classpath: draft.classpath,
      invoice_desc: draft.invoice_desc,
      mobile_desc: draft.mobile_desc,
      short_desc: draft.short_desc,
      long_desc: draft.long_desc,
      attributes: draft.attributes,
    });
  };

  const markReviewed = async () => {
    await onSave(product.id, { status: "reviewed" });
  };

  const autoApproved = product.validation_flags.some((f) => f.field === "status");
  const openFlags = product.validation_flags.filter((f) => f.severity === "warning" || f.severity === "error");

  const btn = "text-[13px] px-3 py-1.5 border transition-colors disabled:opacity-45 whitespace-nowrap";
  const btnStyle = { borderColor: "var(--rule)", color: "var(--ink-2)", borderRadius: 3 };

  return (
    <div className="max-w-[1080px] mx-auto px-8 pb-24">
      <div className="pt-8 pb-6 flex items-center justify-between gap-6">
        <button
          onClick={onBack}
          className="text-[13px] whitespace-nowrap transition-colors hover:text-[color:var(--ink)]"
          style={{ color: "var(--ink-3)" }}
        >
          ← Catalog
        </button>
        <div className="flex items-center gap-4">
          <StampBadge status={product.status} autoApproved={autoApproved} />
          <div className="flex gap-2">
            {product.status === "pending" && (
              <button
                onClick={markReviewed}
                disabled={saving}
                className={btn}
                style={{ ...btnStyle, borderColor: "var(--ink)", color: "var(--paper)", backgroundColor: "var(--ink)" }}
              >
                Approve
              </button>
            )}
            {editing ? (
              <button onClick={handleSaveEdits} disabled={saving} className={btn} style={btnStyle}>
                {saving ? "Saving…" : "Save changes"}
              </button>
            ) : (
              <button onClick={() => setEditing(true)} className={btn} style={btnStyle}>
                Edit
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="border-t pt-8" style={{ borderColor: "var(--rule)" }}>
        <h1 className="text-[26px] leading-[1.15] font-semibold tracking-[-0.03em] max-w-[42ch]">
          {product.short_desc.value}
        </h1>
        <p className="font-mono text-[11px] mt-2.5" style={{ color: "var(--ink-4)" }}>
          {product.raw_mfg_part_num}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,2.1fr)] gap-10 lg:gap-16 mt-10">
        {/* AS SUBMITTED — what the distributor actually sent */}
        <div>
          <div className="eyebrow pb-3 mb-5 border-b" style={{ borderColor: "var(--rule)" }}>
            As submitted
          </div>
          <RawField label="Mfg_Part_Num" value={product.raw_mfg_part_num} />
          <RawField label="Part_Desc" value={product.raw_part_desc} />
          <RawField label="Part_Manuf" value={product.raw_part_manuf} />

          <div className="mt-10">
            <div className="eyebrow pb-3 mb-4 border-b" style={{ borderColor: "var(--rule)" }}>
              Checks {openFlags.length > 0 && `· ${openFlags.length} open`}
            </div>
            <ValidationFlags flags={product.validation_flags} />
          </div>
        </div>

        {/* ENRICHED */}
        <div>
          <div className="eyebrow pb-3 mb-1 border-b" style={{ borderColor: "var(--rule)" }}>
            Enriched
          </div>

          <Field
            label="Manufacturer"
            field={{
              ...product.manufacturer_name,
              value: editing ? draft.manufacturer_name : product.manufacturer_name.value,
            }}
            editing={editing}
            onChange={(v) => setDraft((d) => ({ ...d, manufacturer_name: v }))}
          />
          <Field
            label="Brand"
            field={{ ...product.brand_name, value: editing ? draft.brand_name : product.brand_name.value }}
            editing={editing}
            onChange={(v) => setDraft((d) => ({ ...d, brand_name: v }))}
          />
          <Field
            label="Classpath"
            field={{ ...product.classpath, value: editing ? draft.classpath : product.classpath.value }}
            editing={editing}
            onChange={(v) => setDraft((d) => ({ ...d, classpath: v }))}
          />

          <div className="eyebrow pt-9 pb-3 mb-1 border-b" style={{ borderColor: "var(--rule)" }}>
            Descriptions · four lengths, four rules
          </div>
          <Field
            label="Invoice"
            field={{ ...product.invoice_desc, value: editing ? draft.invoice_desc : product.invoice_desc.value }}
            editing={editing}
            onChange={(v) => setDraft((d) => ({ ...d, invoice_desc: v }))}
            meta={<CharCount value={editing ? draft.invoice_desc : product.invoice_desc.value} max={40} />}
          />
          <Field
            label="Mobile"
            field={{ ...product.mobile_desc, value: editing ? draft.mobile_desc : product.mobile_desc.value }}
            editing={editing}
            onChange={(v) => setDraft((d) => ({ ...d, mobile_desc: v }))}
            meta={<CharCount value={editing ? draft.mobile_desc : product.mobile_desc.value} min={60} max={80} />}
          />
          <Field
            label="Title"
            field={{ ...product.short_desc, value: editing ? draft.short_desc : product.short_desc.value }}
            editing={editing}
            onChange={(v) => setDraft((d) => ({ ...d, short_desc: v }))}
          />
          <Field
            label="Long"
            field={{ ...product.long_desc, value: editing ? draft.long_desc : product.long_desc.value }}
            editing={editing}
            multiline
            onChange={(v) => setDraft((d) => ({ ...d, long_desc: v }))}
          />

          <div className="eyebrow pt-9 pb-3 mb-1 border-b" style={{ borderColor: "var(--rule)" }}>
            Attributes
          </div>
          {product.attributes.map((attr) => (
            <Field
              key={attr.label}
              label={attr.uom ? `${attr.label} · ${attr.uom}` : attr.label}
              field={{ ...attr, value: editing ? draft.attributes[attr.label] ?? attr.value : attr.value }}
              editing={editing}
              onChange={(v) => setDraft((d) => ({ ...d, attributes: { ...d.attributes, [attr.label]: v } }))}
              meta={
                attr.lov_compliant === false ? (
                  <span
                    className="font-mono text-[10px] tracking-[0.04em] whitespace-nowrap"
                    style={{ color: "var(--signal)" }}
                    title="Value falls outside the controlled vocabulary"
                  >
                    off-vocabulary
                  </span>
                ) : undefined
              }
            />
          ))}
        </div>
      </div>
    </div>
  );
}
