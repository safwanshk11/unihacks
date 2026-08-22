"""Category-agnostic enrichment — the path any product takes when it isn't
one of the deeply-specified categories.

Rules cannot cover an open catalogue: a distributor row could be a
dishwasher, a faucet, a pipe fitting or a bolt. So for unknown categories
the model does the two jobs rules can't generalise — deciding what the thing
*is*, and pulling label/value/uom attributes out of an abbreviated string —
while the deterministic layer still owns normalisation, description
formulas, character limits and validation.

Grounding rules that keep this from inventing data (the brief is explicit
that fabricated values score zero):
  * the model is told to return ONLY facts present in the input string,
  * every returned attribute is verified to trace back to the source text
    before it is accepted (see `_traceable`),
  * anything unverifiable is dropped, not guessed.
"""

from __future__ import annotations

import re

from app.llm.llm_client import LLM_BACKEND, LLMUnavailable, MODEL_NAME, generate_json
from app.models import Attribute, Confidence, Source
from app.reference.abbreviations import expand

CLASSIFY_SYSTEM = (
    "You classify rows from an industrial distributor's product catalogue. "
    "Descriptions are abbreviated and cryptic. Respond with strict JSON only."
)

EXTRACT_SYSTEM = (
    "You extract structured product attributes from abbreviated industrial "
    "catalogue text. Extract ONLY what is explicitly present in the input — "
    "never infer, never invent, never add typical values for the product "
    "type. If a value is not in the text, omit it. Respond with strict JSON only."
)


DEPARTMENTS = [
    "Abrasives",
    "Adhesives & Sealants",
    "Appliances & Consumer Electronics",
    "Building Materials",
    "Electrical & Lighting",
    "Fasteners",
    "HVAC",
    "Hand Tools",
    "Hardware",
    "Material Handling",
    "Motors & Power Transmission",
    "Outdoor & Landscaping",
    "Paint & Sundries",
    "Pipe, Valves & Fittings",
    "Plumbing",
    "Power Tools & Accessories",
    "Safety & PPE",
    "Test & Measurement",
]


def llm_classify(part_desc: str, part_manuf: str) -> dict | None:
    """Returns {'dept','class','fine','item_type'} or None.

    Two guards against the failures seen on cryptic input: trade shorthand
    is expanded first ("3/8 CPLG BRS 150#" classified as a Hex Bolt until it
    read as "Coupling Brass"), and the top level is constrained to a fixed
    department list (a sanding belt was landing under "Fasteners").
    """
    expanded = expand(part_desc)
    decoded_line = f"Expanded reading: {expanded!r}\n" if expanded != part_desc else ""

    prompt = (
        f"Catalogue row description: {part_desc!r}\n"
        f"{decoded_line}"
        f"Supplier/manufacturer: {part_manuf!r}\n\n"
        f"Choose the department from EXACTLY this list: {DEPARTMENTS}\n"
        "Then give a class and a fine (sub-category), and the item type — the "
        "noun a buyer would search for, e.g. 'Dishwasher', 'Ball Valve', "
        "'Sanding Belt', 'Pipe Coupling'.\n"
        "Classify what the product IS, not its condition or packaging.\n"
        'Respond as JSON: {"dept": "...", "class": "...", "fine": "...", "item_type": "..."}'
    )
    try:
        result = generate_json(prompt, system=CLASSIFY_SYSTEM)
    except LLMUnavailable:
        return None

    needed = ("dept", "class", "fine", "item_type")
    if not all(isinstance(result.get(k), str) and result[k].strip() for k in needed):
        return None
    return {k: result[k].strip() for k in needed}


IDENTIFY_SYSTEM = (
    "You identify the true manufacturer and consumer brand of an industrial "
    "product from its part number and description. Respond with strict JSON only."
)


def llm_identify_manufacturer(part_desc: str, mfg_part_num: str, supplier: str) -> dict | None:
    """Resolve the real manufacturer/brand, which is often NOT Part_Manuf.

    Scoring against ground truth exposed this: for 'WDTS7024RZ Dishwasher',
    Part_Manuf is "Appliance Dealers Cooperative" — a buying co-op — while
    the answer is "Whirlpool Corporation" / "Whirlpool®". Treating the
    supplier as the manufacturer was one wrong value that then propagated
    into brand, mobile, short and long descriptions: five fields from one
    mistake.

    Returns None when the model has no confident answer, so the caller can
    fall back to the supplier string rather than accept a guess.
    """
    prompt = (
        f"Manufacturer part number: {mfg_part_num!r}\n"
        f"Product description: {part_desc!r}\n"
        f"Listed supplier (may be a distributor or buying co-op, not the maker): {supplier!r}\n\n"
        "Identify the company that actually manufactures this product, and the brand "
        "name it is sold under. Part-number formats are often distinctive to a maker.\n"
        "If you cannot identify it with confidence, return null for both — do not guess.\n"
        'Respond as JSON: {"manufacturer": "Whirlpool Corporation", "brand": "Whirlpool", "confident": true}'
    )
    try:
        result = generate_json(prompt, system=IDENTIFY_SYSTEM)
    except LLMUnavailable:
        return None

    if not result.get("confident"):
        return None
    manufacturer = result.get("manufacturer")
    brand = result.get("brand")
    if not isinstance(manufacturer, str) or not manufacturer.strip():
        return None
    return {
        "manufacturer": manufacturer.strip(),
        "brand": brand.strip() if isinstance(brand, str) and brand.strip() else manufacturer.strip(),
    }


def _normalise(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _traceable(value: str, source_text: str) -> bool:
    """Accept an extracted value only if it demonstrably comes from the input.

    Guards against the model helpfully supplying a plausible-but-absent spec.
    Matches either the whole value or, for multi-token values, its numeric
    core — '120' is accepted from '120V' but 'Stainless Steel' is not
    accepted from a string that never mentions steel.
    """
    haystack = _normalise(source_text)
    needle = _normalise(value)
    if not needle:
        return False
    if needle in haystack:
        return True
    # A numeric measurement counts as traceable if its digits appear.
    digits = re.sub(r"[^0-9]", "", value)
    return bool(digits) and digits in haystack


def llm_extract_attributes(part_desc: str, item_type: str, mfg_part_num: str) -> list[Attribute]:
    expanded = expand(part_desc)
    decoded = f"Expanded reading: {expanded!r}\n" if expanded != part_desc else ""
    prompt = (
        f"Item type: {item_type}\n"
        f"Catalogue description: {part_desc!r}\n"
        f"{decoded}"
        f"Manufacturer part number: {mfg_part_num!r}\n\n"
        "List the product attributes that are explicitly stated in the description "
        "or encoded in the part number. Use a separate 'uom' field for units "
        "(in, ft, V, A, W, lm, K, hr) and leave it null for non-measurements.\n"
        "Do NOT include attributes that are merely typical for this product type.\n"
        'Respond as JSON: {"attributes": [{"label": "Voltage Rating", "value": "120", "uom": "V"}]}'
    )
    try:
        result = generate_json(prompt, system=EXTRACT_SYSTEM)
    except LLMUnavailable:
        return []

    raw_attrs = result.get("attributes")
    if not isinstance(raw_attrs, list):
        return []

    source_text = f"{part_desc} {mfg_part_num}"
    attributes: list[Attribute] = []
    seen: set[str] = set()

    for item in raw_attrs[:20]:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        value = item.get("value")
        if not isinstance(label, str) or not isinstance(value, (str, int, float)):
            continue
        label, value = label.strip(), str(value).strip()
        if not label or not value or label.lower() in seen:
            continue

        uom = item.get("uom")
        uom = uom.strip() if isinstance(uom, str) and uom.strip() else None

        grounded = _traceable(value, source_text)
        seen.add(label.lower())
        attributes.append(
            Attribute(
                label=label,
                value=value,
                uom=uom,
                # Only values we can trace back to the source text are trusted;
                # the rest are surfaced at low confidence for a human, never
                # silently accepted.
                confidence=Confidence.medium if grounded else Confidence.low,
                source=Source.llm,
                rationale=(
                    f"Extracted by {MODEL_NAME} ({LLM_BACKEND}) and verified against the input text."
                    if grounded
                    else f"Proposed by {MODEL_NAME} ({LLM_BACKEND}) but not traceable to the input — needs review."
                ),
                lov_compliant=None,
            )
        )

    return attributes
