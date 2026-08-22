"""The enrichment orchestrator.

Routing, per row:

  1. Manufacturer / brand normalisation — deterministic, every category.
  2. Classification — the lighting specialist gets first refusal; anything
     it does not positively recognise goes to the model, which can classify
     an open catalogue (dishwasher, faucet, fitting, bolt) the way a fixed
     keyword table never could.
  3. Attributes — specialist extractors for recognised lighting rows (finish
     codes in MPN suffixes, ANSI bulb shapes, CCT); model extraction,
     verified against the source text, for everything else.
  4. Descriptions, UOM normalisation, character limits, validation —
     deterministic, every category.

So depth where a category is specified, and correct-if-shallower behaviour
everywhere else. Nothing silently mislabels.
"""

from __future__ import annotations

from app.llm.base import EnrichmentProvider
from app.llm.generic_enrichment import llm_classify, llm_extract_attributes
from app.llm.lighting_provider import (
    build_descriptions,
    classify_lighting,
    extract_lighting_attributes,
    resolve_manufacturer_and_brand,
)
from app.llm.llm_client import LLM_BACKEND, LLMUnavailable, MODEL_NAME, generate_json, is_available
from app.models import (
    Attribute,
    Confidence,
    EnrichedField,
    EnrichedProduct,
    RawProductIn,
    Severity,
    Source,
    ValidationFlag,
)

DESCRIBE_SYSTEM = (
    "You write short, factual product copy for an industrial-commerce catalogue listing. "
    "Use only the facts you are given — never invent a specification, dimension, or feature "
    "that isn't listed. Respond with strict JSON only, no commentary."
)


def _llm_long_desc(product: EnrichedProduct) -> str | None:
    facts = {"Manufacturer": product.manufacturer_name.value, "Brand": product.brand_name.value}
    if product.item_type:
        facts["Item Type"] = product.item_type
    for a in product.attributes:
        if a.value and a.value != "Not specified":
            facts[a.label] = f"{a.value} {a.uom}".strip() if a.uom else a.value
    facts_line = "; ".join(f"{k}={v}" for k, v in facts.items())

    prompt = (
        f"Facts: {facts_line}\n"
        "Write ONE fluent sentence describing this product for a catalogue listing, using ONLY "
        "the facts above.\n"
        'Respond as JSON: {"long_desc": "..."}'
    )
    try:
        result = generate_json(prompt, system=DESCRIBE_SYSTEM)
    except LLMUnavailable:
        return None
    value = result.get("long_desc")
    if not isinstance(value, str) or not value.strip() or len(value) > 400:
        return None
    return value.strip()


class HybridEnrichmentProvider(EnrichmentProvider):
    def enrich(self, raw: RawProductIn) -> EnrichedProduct:
        flags: list[ValidationFlag] = []
        manufacturer_name, brand_name, trade = resolve_manufacturer_and_brand(raw)

        # --- 2. classification -----------------------------------------
        lighting = classify_lighting(raw.part_desc, trade)
        llm_up = is_available()

        if lighting is not None:
            item_type, classpath_value, is_bulb = lighting
            classpath = EnrichedField(
                value=classpath_value,
                confidence=Confidence.high,
                source=Source.inferred,
                rationale=f"Matched lighting keywords in the description to '{item_type}'.",
            )
            attributes = extract_lighting_attributes(raw.mfg_part_num, raw.part_desc, item_type, is_bulb)
        else:
            classified = llm_classify(raw.part_desc, raw.part_manuf) if llm_up else None
            if classified:
                item_type = classified["item_type"]
                classpath_value = f"{classified['dept']} > {classified['class']} > {classified['fine']}"
                classpath = EnrichedField(
                    value=classpath_value,
                    confidence=Confidence.medium,
                    source=Source.llm,
                    rationale=(
                        f"No specialist category matched, so {MODEL_NAME} ({LLM_BACKEND}) classified "
                        "the row from its raw description."
                    ),
                )
                attributes = llm_extract_attributes(raw.part_desc, item_type, raw.mfg_part_num)
            else:
                # Neither a specialist match nor a reachable model: say so
                # rather than guessing a category.
                item_type = ""
                classpath = EnrichedField(
                    value="Unclassified",
                    confidence=Confidence.low,
                    source=Source.inferred,
                    rationale=(
                        "No specialist category matched and the model was unreachable — "
                        "this row needs a human to classify it."
                    ),
                )
                attributes = []
                flags.append(
                    ValidationFlag(
                        field="classpath",
                        issue=f"Could not classify — {LLM_BACKEND} unreachable and no rule matched.",
                        severity=Severity.error,
                    )
                )

        # --- 4. descriptions -------------------------------------------
        noun = item_type or "Product"
        invoice_desc, mobile_desc, short_desc, long_desc = build_descriptions(
            manufacturer_name.value, brand_name.value, noun, raw.mfg_part_num, attributes
        )

        product = EnrichedProduct(
            raw_mfg_part_num=raw.mfg_part_num,
            raw_part_desc=raw.part_desc,
            raw_part_manuf=raw.part_manuf,
            raw_e1_brand=raw.e1_brand,
            raw_unilog_brand=raw.unilog_brand,
            raw_dib_brand=raw.dib_brand,
            manufacturer_name=manufacturer_name,
            brand_name=brand_name,
            classpath=classpath,
            item_type=item_type,
            invoice_desc=invoice_desc,
            mobile_desc=mobile_desc,
            short_desc=short_desc,
            long_desc=long_desc,
            attributes=attributes,
            features=[
                f"{a.label}: {a.value} {a.uom}".strip() if a.uom else f"{a.label}: {a.value}"
                for a in attributes
                if a.value and a.value != "Not specified"
            ][:20],
            validation_flags=flags,
        )

        # --- grounded long description ---------------------------------
        if llm_up:
            grounded = _llm_long_desc(product)
            if grounded:
                product.long_desc = EnrichedField(
                    value=grounded,
                    confidence=Confidence.medium,
                    source=Source.llm,
                    rationale=(
                        f"Written by {MODEL_NAME} ({LLM_BACKEND}), grounded strictly in the "
                        "already-extracted attributes above."
                    ),
                )
            else:
                product.validation_flags.append(
                    ValidationFlag(
                        field="llm",
                        issue=f"Call to {LLM_BACKEND} failed for this item — used the rule-based description instead.",
                        severity=Severity.info,
                    )
                )
        else:
            product.validation_flags.append(
                ValidationFlag(
                    field="llm",
                    issue=f"LLM backend '{LLM_BACKEND}' not reachable — this item used the rule-based pipeline only.",
                    severity=Severity.info,
                )
            )

        return product
