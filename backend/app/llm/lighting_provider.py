"""Enrichment pipeline for the lighting-fixtures slice of the real Unilog
catalog. Deterministic, regex/dictionary-driven — no external API calls,
same EnrichmentProvider contract a real LLM provider would implement.

Pipeline steps (see plan): input analysis -> classification -> attribute
extraction -> cleansing/normalization -> description building. De-dup runs
separately, batch-wide, in app/dedup.py.
"""

from __future__ import annotations

import re

from app.llm.base import EnrichmentProvider
from app.models import Attribute, Confidence, EnrichedField, EnrichedProduct, RawProductIn, Source
from app.reference.decimal_fraction import decimal_to_fraction
from app.reference.lighting_lov import is_lov_compliant
from app.reference.manufacturer_lookup import clean_manufacturer_name, is_placeholder, trade_name
from app.reference.uom import format_with_uom

# --- Step 3: taxonomy & classification ---------------------------------

FIXTURE_PATTERNS: list[tuple[str, str, str]] = [
    # (regex, fixture type label, classpath leaf)
    (r"\bchand(elier)?\b", "Chandelier", "Chandeliers"),
    (r"\bpendant\b", "Pendant Light", "Pendant Lights"),
    (r"\bwall sconce\b", "Wall Sconce", "Wall Sconces"),
    (r"\bwall l(t|ight)\b", "Wall Sconce", "Wall Sconces"),
    (r"\bbath l(t|ight)\b", "Bath & Vanity Light", "Bath & Vanity Lighting"),
    (r"\bdown\s?light\b|\bdown lt\b|\bd/w downlight\b", "Downlight", "Downlights & Recessed Lighting"),
    (r"\bflat panel\b", "Flat Panel Light", "Flat Panel Lighting"),
    (r"\bstrip light\b|\btape light\b", "LED Strip Light", "LED Strip & Tape Lighting"),
    (r"\bwrap l(t|ight)\b", "LED Wrap Light", "LED Wrap Lighting"),
    (r"\bshop light\b", "Shop Light", "Shop Lights"),
    (r"\bhighbay\b", "Highbay Light", "Highbay Lighting"),
    (r"\bpost l(t|ight)\b", "Post Light", "Outdoor Post Lighting"),
    (r"\bwork light\b", "Work Light", "Portable Work Lighting"),
    (r"\bceiling l(t|ight)\b", "Ceiling Light", "Ceiling Lights"),
]

MOUNTING_BY_FIXTURE = {
    "Chandelier": "Suspended Mount",
    "Pendant Light": "Suspended Mount",
    "Wall Sconce": "Wall Mount",
    "Bath & Vanity Light": "Wall Mount",
    "Downlight": "Recessed Mount",
    "Flat Panel Light": "Surface Mount",
    "LED Strip Light": "Surface Mount",
    "LED Wrap Light": "Surface Mount",
    "Shop Light": "Surface Mount",
    "Highbay Light": "Suspended Mount",
    "Ceiling Light": "Ceiling Mount",
    "Post Light": "Post Mount",
    "Work Light": "Portable",
    "Flashlight": "Handheld",
    "General Lighting Fixture": "Surface Mount",
}

# Full classpath for every fixture/lamp type label, built once so
# hybrid_provider.py can reclassify an item (e.g. from an LLM call) without
# duplicating the leaf-mapping logic scattered across FIXTURE_PATTERNS and
# _classify_bulb.
FIXTURE_TYPE_CLASSPATH: dict[str, str] = {
    label: f"Electrical & Lighting > Lighting Fixtures > {leaf}" for _, label, leaf in FIXTURE_PATTERNS
}
FIXTURE_TYPE_CLASSPATH["General Lighting Fixture"] = "Electrical & Lighting > Lighting Fixtures > General Lighting"
FIXTURE_TYPE_CLASSPATH["Flashlight"] = "Electrical & Lighting > Portable Lighting > Flashlights"
FIXTURE_TYPE_CLASSPATH["LED Lamp"] = "Electrical & Lighting > Lamps & Bulbs > LED Lamps"
FIXTURE_TYPE_CLASSPATH["HID Lamp"] = "Electrical & Lighting > Lamps & Bulbs > HID Lamps"
FIXTURE_TYPE_CLASSPATH["Fluorescent Lamp"] = "Electrical & Lighting > Lamps & Bulbs > Fluorescent Lamps"
FIXTURE_TYPE_CLASSPATH["Halogen Lamp"] = "Electrical & Lighting > Lamps & Bulbs > Halogen Lamps"
FIXTURE_TYPE_CLASSPATH["Incandescent Lamp"] = "Electrical & Lighting > Lamps & Bulbs > Incandescent Lamps"

LAMP_LABELS = {"LED Lamp", "HID Lamp", "Fluorescent Lamp", "Halogen Lamp", "Incandescent Lamp"}

# A distributor SKU list this size turned out to span two real Unilog
# sub-taxonomies, not one: "fixtures" (Kichler/Satco wall/ceiling/pendant
# lights) and "lamps/bulbs" (Phillips A19/BR30/etc. replacement bulbs, sold
# by wattage + base + shape, not by fixture type). Detected after the first
# pass classified 60% of Phillips rows as a "General" fallback — this
# handles that properly instead of forcing them into the fixture schema.
BULB_SHAPE_CODES = {
    "A15", "A19", "A21", "A23",
    "ST18", "ST19",
    "BR30", "BR40",
    "R20", "R30",
    "MR16",
    "PAR16", "PAR20", "PAR30", "PAR38",
    "G25",
}
BULB_BASE_WORDS = {"med": "Medium (E26)", "cand": "Candelabra (E12)"}


def _bulb_shape(part_desc: str) -> str | None:
    for token in re.findall(r"[A-Za-z]+\d{2}", part_desc):
        if token.upper() in BULB_SHAPE_CODES:
            return token.upper()
    return None


def _is_bulb(part_desc: str) -> bool:
    if _bulb_shape(part_desc):
        return True
    if re.search(r"\b(sodium|bulb|halogen|incan|retro)\b", part_desc, re.IGNORECASE):
        return True
    if re.search(r"\b(med|cand)\b", part_desc, re.IGNORECASE):
        return True
    has_wattage = re.search(r"\b\d{1,3}w(?![a-zA-Z])", part_desc, re.IGNORECASE)
    has_cct = re.search(r"\b\d{2}k\b|\bmulti cct\b", part_desc, re.IGNORECASE)
    has_pack = re.search(r"\b\d{1,2}\s?pk\b", part_desc, re.IGNORECASE)
    if has_wattage and (has_cct or has_pack):
        return True
    if re.search(r"\bflor\b", part_desc, re.IGNORECASE) and re.search(r"\bt\d{1,2}\b", part_desc, re.IGNORECASE):
        return True
    return False


def _classify_bulb(part_desc: str) -> tuple[str, str]:
    if re.search(r"\bsodium\b", part_desc, re.IGNORECASE):
        return "HID Lamp", "Electrical & Lighting > Lamps & Bulbs > HID Lamps"
    if re.search(r"\bflor\b", part_desc, re.IGNORECASE):
        return "Fluorescent Lamp", "Electrical & Lighting > Lamps & Bulbs > Fluorescent Lamps"
    if re.search(r"\bhalogen\b", part_desc, re.IGNORECASE):
        return "Halogen Lamp", "Electrical & Lighting > Lamps & Bulbs > Halogen Lamps"
    if re.search(r"\bincan\b", part_desc, re.IGNORECASE):
        return "Incandescent Lamp", "Electrical & Lighting > Lamps & Bulbs > Incandescent Lamps"
    return "LED Lamp", "Electrical & Lighting > Lamps & Bulbs > LED Lamps"


LIGHTING_MANUFACTURERS = {"Kichler", "Satco", "Phillips", "Feit Electric", "Streamlight"}


def classify_lighting(part_desc: str, manufacturer_trade_name: str | None) -> tuple[str, str, bool] | None:
    """Returns (item_type, classpath, is_bulb), or None when this row is not
    recognisably a lighting product.

    Returning None is the important part: this is a *specialist* layer, and a
    specialist that claims every row is why a dishwasher once came out of
    here as a 'General Lighting Fixture'. Anything unmatched now falls
    through to the category-agnostic path instead.
    """
    if manufacturer_trade_name == "Streamlight":
        return "Flashlight", "Electrical & Lighting > Portable Lighting > Flashlights", False

    for pattern, label, leaf in FIXTURE_PATTERNS:
        if re.search(pattern, part_desc, re.IGNORECASE):
            return label, f"Electrical & Lighting > Lighting Fixtures > {leaf}", False

    if _is_bulb(part_desc):
        # Bulb heuristics lean on wattage/CCT/pack patterns that also appear
        # outside lighting, so only trust them for a known lighting supplier.
        if manufacturer_trade_name in LIGHTING_MANUFACTURERS:
            label, classpath = _classify_bulb(part_desc)
            return label, classpath, True

    return None


# --- Step 4: attribute extraction ---------------------------------------

# Ordered longest-code-first so e.g. "DBK" is checked before "BK".
FINISH_CODES: list[tuple[str, str]] = [
    ("CPZLED", "Champagne Bronze"),
    ("BKCLR", "Black (Clear Glass Accent)"),
    ("BKCS", "Black (Clear Seeded Glass)"),
    ("DBK", "Distressed Black"),
    ("AVI", "Anvil Iron"),
    ("CPZ", "Champagne Bronze"),
    ("BK", "Black"),
    ("NI", "Brushed Nickel"),
    ("CH", "Chrome"),
    ("WH", "White"),
]

FINISH_WORDS = {
    "bk": "Black",
    "black": "Black",
    "wh": "White",
    "white": "White",
    "bn": "Brushed Nickel",
    "nickel": "Brushed Nickel",
    "chrome": "Chrome",
}


def _extract_finish(mpn: str, part_desc: str) -> Attribute:
    suffix_match = re.search(r"([A-Za-z]+)$", mpn)
    if suffix_match:
        suffix = suffix_match.group(1)
        for code, name in FINISH_CODES:
            if code in suffix:
                return Attribute(
                    label="Finish",
                    value=name,
                    confidence=Confidence.high,
                    source=Source.input,
                    rationale=f"Finish code '{code}' found in the part number suffix ('{mpn}').",
                    lov_compliant=is_lov_compliant("Finish", name),
                )

    tokens = re.findall(r"[A-Za-z]+", part_desc)
    if tokens:
        last = tokens[-1].lower()
        if last in FINISH_WORDS:
            name = FINISH_WORDS[last]
            return Attribute(
                label="Finish",
                value=name,
                confidence=Confidence.high,
                source=Source.input,
                rationale=f"Trailing color word '{tokens[-1]}' found in the description.",
                lov_compliant=is_lov_compliant("Finish", name),
            )

    return Attribute(
        label="Finish",
        value="Not specified",
        confidence=Confidence.low,
        source=Source.inferred,
        rationale="No finish code found in the part number or description.",
        lov_compliant=is_lov_compliant("Finish", "Not specified"),
    )


def _extract_cct(part_desc: str) -> Attribute | None:
    m = re.search(r"\b(\d{2})k\b", part_desc, re.IGNORECASE)
    if m:
        kelvin = int(m.group(1)) * 100
        return Attribute(
            label="Color Temperature",
            value=str(kelvin),
            uom="K",
            confidence=Confidence.high,
            source=Source.input,
            rationale=f"'{m.group(0)}' in the description parsed as {kelvin}K.",
            lov_compliant=None,
        )
    m = re.search(r"\b(\d)\s?cct\b", part_desc, re.IGNORECASE)
    if m:
        return Attribute(
            label="Color Temperature",
            value=f"Selectable ({m.group(1)} CCT presets)",
            confidence=Confidence.high,
            source=Source.input,
            rationale="Description states a multi-CCT selectable fixture.",
            lov_compliant=None,
        )
    if re.search(r"\bmulti cct\b", part_desc, re.IGNORECASE):
        return Attribute(
            label="Color Temperature",
            value="Selectable (Multi-CCT)",
            confidence=Confidence.high,
            source=Source.input,
            rationale="Description states a multi-CCT selectable fixture.",
            lov_compliant=None,
        )
    return None


def _extract_wattage(part_desc: str) -> Attribute | None:
    m = re.search(r"\b(\d{1,3})w(?![a-zA-Z])", part_desc, re.IGNORECASE)
    if not m:
        return None
    return Attribute(
        label="Wattage",
        value=m.group(1),
        uom="W",
        confidence=Confidence.high,
        source=Source.input,
        rationale=f"'{m.group(0)}' in the description parsed as {m.group(1)} W.",
        lov_compliant=None,
    )


def _extract_luminous_output(part_desc: str) -> Attribute | None:
    m = re.search(r"\b(\d{3,5})l\b", part_desc, re.IGNORECASE)
    if not m:
        return None
    return Attribute(
        label="Luminous Output",
        value=m.group(1),
        uom="lm",
        confidence=Confidence.high,
        source=Source.input,
        rationale=f"'{m.group(0)}' in the description parsed as {m.group(1)} lm.",
        lov_compliant=None,
    )


def _extract_dimension(part_desc: str) -> Attribute | None:
    m = re.search(r"(\d{1,2})x(\d{1,2})\b", part_desc, re.IGNORECASE)
    if m:
        return Attribute(
            label="Panel Size",
            value=f"{m.group(1)} in x {m.group(2)} in",
            confidence=Confidence.high,
            source=Source.input,
            rationale=f"'{m.group(0)}' in the description parsed as a panel size in inches.",
            lov_compliant=None,
        )
    m = re.search(r'(\d{1,2}(?:\.\d+)?)"', part_desc)
    if m:
        value = float(m.group(1))
        return Attribute(
            label="Diameter/Size",
            value=decimal_to_fraction(value),
            uom="in",
            confidence=Confidence.high,
            source=Source.input,
            rationale=f"'{m.group(0)}' in the description parsed as a diameter in inches.",
            lov_compliant=None,
        )
    m = re.search(r"(\d{1,2}(?:\.\d+)?)'", part_desc)
    if m:
        value = float(m.group(1))
        return Attribute(
            label="Length",
            value=decimal_to_fraction(value),
            uom="ft",
            confidence=Confidence.high,
            source=Source.input,
            rationale=f"'{m.group(0)}' in the description parsed as a length in feet.",
            lov_compliant=None,
        )
    return None


def _extract_bulb_shape(part_desc: str) -> Attribute:
    shape = _bulb_shape(part_desc)
    if shape:
        return Attribute(
            label="Bulb Shape",
            value=shape,
            confidence=Confidence.high,
            source=Source.input,
            rationale=f"ANSI bulb shape code '{shape}' found in the description.",
            lov_compliant=None,
        )
    return Attribute(
        label="Bulb Shape",
        value="Not specified",
        confidence=Confidence.low,
        source=Source.inferred,
        rationale="No ANSI bulb shape code (e.g. A19, BR30) found in the description.",
        lov_compliant=None,
    )


def _extract_base_type(part_desc: str) -> Attribute:
    m = re.search(r"\b(med|cand)\b", part_desc, re.IGNORECASE)
    if m:
        value = BULB_BASE_WORDS[m.group(1).lower()]
        return Attribute(
            label="Base Type",
            value=value,
            confidence=Confidence.high,
            source=Source.input,
            rationale=f"'{m.group(0)}' in the description parsed as a {value} base.",
            lov_compliant=None,
        )
    return Attribute(
        label="Base Type",
        value="Not specified",
        confidence=Confidence.low,
        source=Source.inferred,
        rationale="No base-type code found in the description.",
        lov_compliant=None,
    )


def _extract_pack_qty(part_desc: str) -> Attribute | None:
    m = re.search(r"\b(\d{1,2})\s?pk\b", part_desc, re.IGNORECASE)
    if not m:
        return None
    return Attribute(
        label="Pack Quantity",
        value=f"{m.group(1)}-Pack",
        confidence=Confidence.high,
        source=Source.input,
        rationale=f"'{m.group(0)}' in the description parsed as a {m.group(1)}-count pack.",
        lov_compliant=None,
    )


def _extract_light_source(part_desc: str, fixture_type: str) -> Attribute:
    if re.search(r"\bsodium\b", part_desc, re.IGNORECASE):
        return Attribute(
            label="Light Source",
            value="High Pressure Sodium",
            confidence=Confidence.high,
            source=Source.input,
            rationale="'Sodium' stated explicitly in the description.",
            lov_compliant=is_lov_compliant("Light Source", "High Pressure Sodium"),
        )
    if re.search(r"\bled\b", part_desc, re.IGNORECASE):
        return Attribute(
            label="Light Source",
            value="LED",
            confidence=Confidence.high,
            source=Source.input,
            rationale="'LED' stated explicitly in the description.",
            lov_compliant=is_lov_compliant("Light Source", "LED"),
        )
    if fixture_type in ("Fluorescent Lamp",) or re.search(r"\bflor\b", part_desc, re.IGNORECASE):
        return Attribute(
            label="Light Source",
            value="Fluorescent",
            confidence=Confidence.high,
            source=Source.input,
            rationale="Fluorescent tube designation (T8/T12/T9) found in the description.",
            lov_compliant=is_lov_compliant("Light Source", "Fluorescent"),
        )
    if re.search(r"\bhalogen\b", part_desc, re.IGNORECASE):
        return Attribute(
            label="Light Source",
            value="Halogen",
            confidence=Confidence.high,
            source=Source.input,
            rationale="'Halogen' stated explicitly in the description.",
            lov_compliant=is_lov_compliant("Light Source", "Halogen"),
        )
    if re.search(r"\bincan\b", part_desc, re.IGNORECASE):
        return Attribute(
            label="Light Source",
            value="Incandescent",
            confidence=Confidence.high,
            source=Source.input,
            rationale="'Incan' (incandescent) stated explicitly in the description.",
            lov_compliant=is_lov_compliant("Light Source", "Incandescent"),
        )
    return Attribute(
        label="Light Source",
        value="LED",
        confidence=Confidence.medium,
        source=Source.inferred,
        rationale="Not stated explicitly; most current fixtures in this category are LED.",
        lov_compliant=is_lov_compliant("Light Source", "LED"),
    )


# --- Step 6: description building ----------------------------------------


def _attr_display(attr: Attribute) -> str:
    return format_with_uom(attr.value, attr.uom) if attr.uom else attr.value


def _build_descriptions(
    manufacturer_name: str,
    brand: str,
    fixture_type: str,
    mounting: str | None,
    mpn: str,
    attributes: list[Attribute],
) -> tuple[EnrichedField, EnrichedField, EnrichedField, EnrichedField]:
    finish = next((a for a in attributes if a.label == "Finish"), None)
    finish_value = finish.value if finish and finish.value != "Not specified" else None
    extra = [a for a in attributes if a.label not in ("Fixture Type", "Finish", "Mounting Type", "Light Source")]

    invoice_parts = [fixture_type.upper()]
    if finish_value:
        invoice_parts.append(finish_value.upper())
    for a in extra[:1]:
        invoice_parts.append(_attr_display(a).upper())
    invoice_text = " ".join(invoice_parts)
    invoice_desc = EnrichedField(
        value=invoice_text[:40],
        confidence=Confidence.medium,
        source=Source.inferred,
        rationale="Built from fixture type + finish + a leading spec, capped at 40 characters, CAPS.",
    )

    # Greedily add descriptors (finish, mounting/base, then every extracted
    # attribute) until the string lands in the 60-80 char target from the
    # worked example — real listings pad this out with marketing copy we
    # don't have, so this is an honest best-effort, not a guarantee.
    descriptors = [v for v in [finish_value, mounting] if v] + [_attr_display(a) for a in extra]
    mobile_base = f"{manufacturer_name} {brand}, {fixture_type}"
    used: list[str] = []
    mobile_text = f"{mobile_base}, {mpn}"
    for d in descriptors:
        candidate = f"{mobile_base}, {', '.join(used + [d])}, {mpn}"
        if len(mobile_text) >= 60 and len(candidate) > 80:
            break
        used.append(d)
        mobile_text = candidate
        if len(mobile_text) >= 60:
            break
    mobile_desc = EnrichedField(
        value=mobile_text[:80],
        confidence=Confidence.medium,
        source=Source.inferred,
        rationale="Built as 'Manufacturer Brand, Fixture Type, [attributes], MPN' per the worked-example pattern, padded with attributes to reach the 60-80 char target.",
    )

    short_bits = [f"{brand}®", mpn, fixture_type]
    tail = [v for v in [finish_value, mounting] if v]
    short_text = ", ".join([" ".join(short_bits)] + tail)
    short_desc = EnrichedField(
        value=short_text,
        confidence=Confidence.medium,
        source=Source.inferred,
        rationale="Built as 'Brand® MPN Fixture Type, Finish, Mounting' per the worked-example title pattern.",
    )

    long_bits = [f"{brand}®", fixture_type + ","]
    attr_strs = [_attr_display(a) for a in attributes if a.label not in ("Fixture Type", "Light Source")]
    long_text = " ".join(long_bits) + " " + ", ".join(attr_strs)
    long_desc = EnrichedField(
        value=long_text,
        confidence=Confidence.medium,
        source=Source.inferred,
        rationale="Built from brand, fixture type, and every extracted attribute with its approved UOM.",
    )

    return invoice_desc, mobile_desc, short_desc, long_desc


def extract_lighting_attributes(mfg_part_num: str, part_desc: str, item_type: str, is_bulb: bool) -> list[Attribute]:
    """The specialist extraction layer — only ever called for rows that
    `classify_lighting` positively recognised."""
    light_source_attr = _extract_light_source(part_desc, item_type)
    type_attr = Attribute(
        label="Fixture Type",
        value=item_type,
        confidence=Confidence.high,
        source=Source.inferred,
        rationale=f"Matched keywords in the description to '{item_type}'.",
        lov_compliant=is_lov_compliant("Fixture Type", item_type),
    )

    if is_bulb:
        attributes = [
            type_attr,
            _extract_bulb_shape(part_desc),
            _extract_base_type(part_desc),
            light_source_attr,
        ]
        pack_attr = _extract_pack_qty(part_desc)
        if pack_attr:
            attributes.append(pack_attr)
    else:
        mounting_value = MOUNTING_BY_FIXTURE.get(item_type, "Surface Mount")
        attributes = [
            type_attr,
            _extract_finish(mfg_part_num, part_desc),
            Attribute(
                label="Mounting Type",
                value=mounting_value,
                confidence=Confidence.medium,
                source=Source.inferred,
                rationale=f"Inferred from fixture type ('{item_type}').",
                lov_compliant=is_lov_compliant("Mounting Type", mounting_value),
            ),
            light_source_attr,
        ]

    for extractor in (_extract_cct, _extract_wattage, _extract_luminous_output, _extract_dimension):
        attr = extractor(part_desc)
        if attr:
            attributes.append(attr)

    return attributes


def resolve_manufacturer_and_brand(raw: RawProductIn) -> tuple[EnrichedField, EnrichedField, str]:
    """Category-agnostic — every product goes through this."""
    clean_mfr = clean_manufacturer_name(raw.part_manuf)
    trade = trade_name(clean_mfr) or clean_mfr

    manufacturer_name = EnrichedField(
        value=clean_mfr,
        confidence=Confidence.high,
        source=Source.input,
        rationale="Cleaned from Part_Manuf (stripped the trailing manufacturer code).",
    )

    if is_placeholder(raw.e1_brand):
        brand_name = EnrichedField(
            value=trade,
            confidence=Confidence.medium,
            source=Source.inferred,
            rationale="E1_Brand was a placeholder ('-- Unbranded --'); used the manufacturer's trade name instead, per the brief's own rule.",
        )
    else:
        brand_name = EnrichedField(
            value=raw.e1_brand or "",
            confidence=Confidence.high,
            source=Source.input,
            rationale="Taken directly from E1_Brand.",
        )

    return manufacturer_name, brand_name, trade


def build_descriptions(
    manufacturer_name: str,
    brand: str,
    item_type: str,
    mpn: str,
    attributes: list[Attribute],
):
    """Description formulas are category-agnostic — the worked example's
    shapes hold whether the noun is 'Wall Sconce' or 'Dishwasher'."""
    mounting = next(
        (a.value for a in attributes if a.label == "Mounting Type" and a.value != "Not specified"),
        None,
    )
    return _build_descriptions(manufacturer_name, brand, item_type, mounting, mpn, attributes)
