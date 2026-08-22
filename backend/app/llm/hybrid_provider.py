"""Hybrid enrichment: the deterministic pipeline (LightingEnrichmentProvider)
does structured, auditable extraction — finish codes, dimensions, wattage,
CCT all come straight from the text via regex, which is more reliable and
more auditable than asking a model to read them off. A real LLM (local
Ollama by default, or Gemini — see app/llm/llm_client.py) is layered on top
for the two things a rules engine is genuinely bad at:

1. Classification when the keyword classifier finds nothing (low
   confidence) — a real judgment call from the raw text.
2. Writing the long description as fluent prose grounded *only* in the
   attributes already extracted and validated, instead of comma-joining
   them — matching how Unilog's own worked example actually reads.

Every LLM-touched field is tagged source=llm (not source=inferred) so the
review UI shows exactly which fields came from the rule engine vs. a model
call. If the LLM backend isn't reachable, enrich() falls back to the pure
deterministic result and adds a visible info flag — the app must keep
working either way.
"""

from __future__ import annotations

from app.llm.lighting_provider import FIXTURE_TYPE_CLASSPATH, LAMP_LABELS, LightingEnrichmentProvider
from app.llm.llm_client import LLM_BACKEND, LLMUnavailable, MODEL_NAME, generate_json, is_available
from app.models import Confidence, EnrichedField, EnrichedProduct, RawProductIn, Severity, Source, ValidationFlag
from app.reference.lighting_lov import FIXTURE_TYPE_LOV, is_lov_compliant

CLASSIFY_SYSTEM = (
    "You classify industrial lighting catalog rows into a fixed set of product types. "
    "Respond with strict JSON only, no commentary."
)
DESCRIBE_SYSTEM = (
    "You write short, factual product copy for an industrial-commerce catalog listing. "
    "Use only the facts you are given — never invent a specification, dimension, or feature "
    "that isn't listed. Respond with strict JSON only, no commentary."
)


def _llm_classify(raw: RawProductIn) -> str | None:
    candidates = sorted(FIXTURE_TYPE_LOV)
    prompt = (
        f"Raw catalog description: {raw.part_desc!r}\n"
        f"Manufacturer: {raw.part_manuf!r}\n"
        f"Pick the single best product type from this exact list, copied verbatim: {candidates}\n"
        'Respond as JSON: {"fixture_type": "<one value from the list>"}'
    )
    try:
        result = generate_json(prompt, system=CLASSIFY_SYSTEM)
    except LLMUnavailable:
        return None
    value = result.get("fixture_type")
    return value if value in FIXTURE_TYPE_LOV else None


def _llm_ground_long_desc(product: EnrichedProduct) -> str | None:
    facts = {"Manufacturer": product.manufacturer_name.value, "Brand": product.brand_name.value}
    for a in product.attributes:
        if a.value and a.value != "Not specified":
            facts[a.label] = f"{a.value} {a.uom}".strip() if a.uom else a.value
    facts_line = "; ".join(f"{k}={v}" for k, v in facts.items())

    prompt = (
        f"Facts: {facts_line}\n"
        "Write ONE fluent sentence describing this product for a catalog listing, using ONLY "
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


class HybridEnrichmentProvider(LightingEnrichmentProvider):
    def enrich(self, raw: RawProductIn) -> EnrichedProduct:
        product = super().enrich(raw)

        if not is_available():
            product.validation_flags.append(
                ValidationFlag(
                    field="llm",
                    issue=f"LLM backend '{LLM_BACKEND}' not reachable — this item used the rule-based pipeline only.",
                    severity=Severity.info,
                )
            )
            return product

        if product.classpath.confidence == Confidence.low:
            self._apply_llm_classification(raw, product)

        long_desc_ok = self._apply_llm_long_desc(product)
        if not long_desc_ok:
            product.validation_flags.append(
                ValidationFlag(
                    field="llm",
                    issue=f"Call to {LLM_BACKEND} failed for this item — used the rule-based description instead.",
                    severity=Severity.info,
                )
            )

        return product

    def _apply_llm_classification(self, raw: RawProductIn, product: EnrichedProduct) -> None:
        llm_type = _llm_classify(raw)
        if not llm_type:
            return

        fixture_attr = next((a for a in product.attributes if a.label == "Fixture Type"), None)
        if fixture_attr:
            fixture_attr.value = llm_type
            fixture_attr.confidence = Confidence.medium
            fixture_attr.source = Source.llm
            fixture_attr.rationale = (
                f"Classified by {MODEL_NAME} ({LLM_BACKEND}) — the rule-based classifier "
                "found no keyword match in the description."
            )
            fixture_attr.lov_compliant = is_lov_compliant("Fixture Type", llm_type)

        product.classpath = EnrichedField(
            value=FIXTURE_TYPE_CLASSPATH.get(llm_type, product.classpath.value),
            confidence=Confidence.medium,
            source=Source.llm,
            rationale=f"Classified by {MODEL_NAME} ({LLM_BACKEND}) from the raw description.",
        )
        if llm_type in LAMP_LABELS:
            product.attributes = [a for a in product.attributes if a.label not in ("Finish", "Mounting Type")]

    def _apply_llm_long_desc(self, product: EnrichedProduct) -> bool:
        grounded = _llm_ground_long_desc(product)
        if not grounded:
            return False
        product.long_desc = EnrichedField(
            value=grounded,
            confidence=Confidence.medium,
            source=Source.llm,
            rationale=f"Written by {MODEL_NAME} ({LLM_BACKEND}), grounded strictly in the already-extracted attributes above.",
        )
        return True
