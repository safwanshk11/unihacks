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

const sectionLabel = "text-xs font-medium mt-6 mb-2";
const sectionLabelStyle = { color: "var(--text-faint)" };

function CharCount({ value, min, max }: { value: string; min?: number; max?: number }) {
  const len = value.length;
  const ok = (min === undefined || len >= min) && (max === undefined || len <= max);
  const target = min !== undefined && max !== undefined ? `${min}-${max}` : `≤${max}`;
  return (
    <span className="text-[11px]" style={{ color: ok ? "var(--text-faint)" : "var(--danger)" }}>
      {len} chars (target {target})
    </span>
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

  return (
    <div className="max-w-5xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-5">
        <button onClick={onBack} className="text-sm font-medium" style={{ color: "var(--text-muted)" }}>
          ← Back to catalog
        </button>
        <div className="flex items-center gap-2.5">
          <StampBadge
            status={product.status}
            autoApproved={product.validation_flags.some((f) => f.field === "status")}
          />
          {product.status === "pending" && (
            <button
              onClick={markReviewed}
              disabled={saving}
              className="text-sm font-medium px-3.5 py-2 rounded-lg text-white disabled:opacity-50"
              style={{ backgroundColor: "var(--success)" }}
            >
              Approve
            </button>
          )}
          {editing ? (
            <button
              onClick={handleSaveEdits}
              disabled={saving}
              className="text-sm font-medium px-3.5 py-2 rounded-lg text-white disabled:opacity-50"
              style={{ backgroundColor: "var(--accent)" }}
            >
              {saving ? "Saving…" : "Save changes"}
            </button>
          ) : (
            <button
              onClick={() => setEditing(true)}
              className="text-sm font-medium px-3.5 py-2 rounded-lg border"
              style={{ borderColor: "var(--border)", color: "var(--text)" }}
            >
              Edit
            </button>
          )}
        </div>
      </div>

      <div
        className="rounded-xl border overflow-hidden mb-6"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--surface)" }}
      >
        <div className="grid" style={{ gridTemplateColumns: "minmax(0,1fr) minmax(0,2fr)" }}>
          {/* AS SUBMITTED */}
          <div className="p-6 border-r" style={{ borderColor: "var(--border)" }}>
            <span
              className="inline-block text-xs font-medium px-2 py-1 rounded-md mb-4"
              style={{ backgroundColor: "var(--bg)", color: "var(--text-muted)" }}
            >
              As submitted
            </span>
            <p className="text-xs font-medium mb-1" style={{ color: "var(--text-faint)" }}>
              Mfg_Part_Num
            </p>
            <p className="text-sm mb-4 font-mono">{product.raw_mfg_part_num}</p>
            <p className="text-xs font-medium mb-1" style={{ color: "var(--text-faint)" }}>
              Part_Desc
            </p>
            <p className="text-sm mb-4">{product.raw_part_desc}</p>
            <p className="text-xs font-medium mb-1" style={{ color: "var(--text-faint)" }}>
              Part_Manuf
            </p>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              {product.raw_part_manuf}
            </p>
          </div>

          {/* ENRICHED */}
          <div className="p-6">
            <span
              className="inline-block text-xs font-medium px-2 py-1 rounded-md mb-4"
              style={{ backgroundColor: "var(--accent-soft)", color: "var(--accent)" }}
            >
              Enriched
            </span>

            <Field
              label="Manufacturer Name"
              field={{ ...product.manufacturer_name, value: editing ? draft.manufacturer_name : product.manufacturer_name.value }}
              editing={editing}
              onChange={(v) => setDraft((d) => ({ ...d, manufacturer_name: v }))}
            />
            <Field
              label="Brand Name"
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

            <p className={sectionLabel} style={sectionLabelStyle}>
              Descriptions
            </p>

            <div className="flex items-center justify-between">
              <div />
              <CharCount value={editing ? draft.invoice_desc : product.invoice_desc.value} max={40} />
            </div>
            <Field
              label="Invoice Desc"
              field={{ ...product.invoice_desc, value: editing ? draft.invoice_desc : product.invoice_desc.value }}
              editing={editing}
              onChange={(v) => setDraft((d) => ({ ...d, invoice_desc: v }))}
            />
            <div className="flex items-center justify-between">
              <div />
              <CharCount value={editing ? draft.mobile_desc : product.mobile_desc.value} min={60} max={80} />
            </div>
            <Field
              label="Mobile Desc"
              field={{ ...product.mobile_desc, value: editing ? draft.mobile_desc : product.mobile_desc.value }}
              editing={editing}
              onChange={(v) => setDraft((d) => ({ ...d, mobile_desc: v }))}
            />
            <Field
              label="Short Desc (Title)"
              field={{ ...product.short_desc, value: editing ? draft.short_desc : product.short_desc.value }}
              editing={editing}
              onChange={(v) => setDraft((d) => ({ ...d, short_desc: v }))}
            />
            <Field
              label="Long Desc"
              field={{ ...product.long_desc, value: editing ? draft.long_desc : product.long_desc.value }}
              editing={editing}
              multiline
              onChange={(v) => setDraft((d) => ({ ...d, long_desc: v }))}
            />

            <p className={sectionLabel} style={sectionLabelStyle}>
              Attributes
            </p>
            {product.attributes.map((attr) => (
              <div key={attr.label}>
                <Field
                  label={attr.uom ? `${attr.label} (${attr.uom})` : attr.label}
                  field={{
                    ...attr,
                    value: editing ? draft.attributes[attr.label] ?? attr.value : attr.value,
                  }}
                  editing={editing}
                  onChange={(v) =>
                    setDraft((d) => ({ ...d, attributes: { ...d.attributes, [attr.label]: v } }))
                  }
                />
                {attr.lov_compliant === false && (
                  <p className="text-[11px] -mt-2 mb-2" style={{ color: "var(--warning)" }}>
                    Not in placeholder LOV — verify against Unicat.
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div>
        <p className="text-xs font-medium mb-2" style={{ color: "var(--text-faint)" }}>
          Validation flags ({product.validation_flags.length})
        </p>
        <ValidationFlags flags={product.validation_flags} />
      </div>
    </div>
  );
}
