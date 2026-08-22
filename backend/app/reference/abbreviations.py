"""Trade-abbreviation glossary — the "input analysis" step.

The brief opens with exactly this problem: descriptions arrive as
"3/8 CPLG BRS 150#". A language model asked to classify that cold guesses
badly (observed: "Hex Bolt"). Expanding the trade shorthand first —
"3/8 Coupling Brass 150 Pound Class" — gives both the model and a human
something decodable, and costs one dictionary pass.

The expansion is used only to *inform* classification and extraction. The
raw string is preserved untouched on the record, because Part_Desc has to
round-trip into the Delivery Format verbatim.
"""

from __future__ import annotations

import re

# Deliberately trade-wide rather than category-specific: this runs before we
# know what the product is.
ABBREVIATIONS: dict[str, str] = {
    # --- pipe, valve & fitting ---
    "cplg": "Coupling",
    "cpl": "Coupling",
    "ell": "Elbow",
    "nip": "Nipple",
    "red": "Reducer",
    "bshg": "Bushing",
    "bush": "Bushing",
    "un": "Union",
    "flg": "Flange",
    "vlv": "Valve",
    "npt": "National Pipe Thread",
    "sch": "Schedule",
    "thd": "Thread",
    "thrd": "Thread",
    "od": "Outside Diameter",
    "id": "Inside Diameter",
    "fpt": "Female Pipe Thread",
    "mpt": "Male Pipe Thread",
    # --- materials ---
    "brs": "Brass",
    "brz": "Bronze",
    "ss": "Stainless Steel",
    "sst": "Stainless Steel",
    "galv": "Galvanized",
    "ci": "Cast Iron",
    "mi": "Malleable Iron",
    "alum": "Aluminum",
    "cu": "Copper",
    "zn": "Zinc",
    "pl": "Plated",
    "blk": "Black",
    "chr": "Chrome",
    # --- fasteners ---
    "hex": "Hex",
    "hd": "Head",
    "mach": "Machine",
    "scr": "Screw",
    "wshr": "Washer",
    "lk": "Lock",
    "anch": "Anchor",
    # --- electrical ---
    "brkr": "Breaker",
    "recept": "Receptacle",
    "sw": "Switch",
    "conn": "Connector",
    "cond": "Conduit",
    "ph": "Phase",
    "hp": "Horsepower",
    "flor": "Fluorescent",
    "incan": "Incandescent",
    "cct": "Color Temperature",
    "med": "Medium Base",
    "cand": "Candelabra Base",
    # --- abrasives & tooling ---
    "abr": "Abrasive",
    "grit": "Grit",
    "blde": "Blade",
    "bld": "Blade",
    # --- general ---
    "assy": "Assembly",
    "brkt": "Bracket",
    "lg": "Long",
    "dia": "Diameter",
    "qty": "Quantity",
    "pk": "Pack",
    "pc": "Piece",
    "pcs": "Pieces",
    "ea": "Each",
    "w/": "With",
    "w/o": "Without",
    "adj": "Adjustable",
    "std": "Standard",
    "hvy": "Heavy",
    "lt": "Light",
    "ext": "Extension",
    "int": "Interior",
    "reg": "Regular",
}

# "150#" is a pressure class in pipe, not a weight.
_POUND_CLASS = re.compile(r"\b(\d{2,4})#")
_TOKEN = re.compile(r"[A-Za-z]+/?[A-Za-z]*")


def expand(part_desc: str) -> str:
    """Expand trade shorthand for downstream reading. Never mutates the
    stored raw description."""
    text = _POUND_CLASS.sub(lambda m: f"{m.group(1)} Pound Class", part_desc)

    def swap(match: re.Match) -> str:
        token = match.group(0)
        replacement = ABBREVIATIONS.get(token.lower())
        if replacement is None:
            return token
        # A count runs straight into its unit in this shorthand ("6pc"), so
        # reinsert the space the expansion needs to stay readable.
        start = match.start()
        if start > 0 and text[start - 1].isdigit():
            return " " + replacement
        return replacement

    return _TOKEN.sub(swap, text)


def expansion_note(original: str, expanded: str) -> str | None:
    """Human-readable record of what the glossary changed, for the rationale
    trail — an empty note means the string needed no decoding."""
    if expanded.strip().lower() == original.strip().lower():
        return None
    return f"Trade abbreviations expanded for analysis: {original!r} → {expanded!r}"
