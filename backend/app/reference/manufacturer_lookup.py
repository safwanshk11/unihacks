"""Manufacturer/brand normalization for the lighting-fixture slice.

PLACEHOLDER: derived only from the manufacturer strings actually present in
this dataset's Part_Manuf column, not Unilog's real 27,000-row
UniCat_Manufacturer_and_Brand_List.xlsx (not available on this machine,
which carries exact legal casing/suffixes/(R)/(TM) symbols). Swap
MANUFACTURER_TRADE_NAME for a real lookup against that file when available.

PLACEHOLDER_TOKENS mirrors the brief's note that "-- Unbranded --" /
"-- No Unilog Brand --" / "-- No DIB Brand --" mean the field is empty.
"""

import re

PLACEHOLDER_TOKENS = {
    "-- unbranded --",
    "-- no unilog brand --",
    "-- no dib brand --",
    "",
}

# Trade/short name to use in generated copy, keyed by the raw Part_Manuf
# string with its trailing "(CODE)" stripped. Built from this dataset only.
MANUFACTURER_TRADE_NAME = {
    "kichler lighting": "Kichler",
    "satco prod inc": "Satco",
    "phillips lighting": "Phillips",
    "feit electric": "Feit Electric",
    "streamlight": "Streamlight",
}


def is_placeholder(value: str | None) -> bool:
    return (value or "").strip().lower() in PLACEHOLDER_TOKENS


def clean_manufacturer_name(raw_part_manuf: str) -> str:
    """'Kichler Lighting (KICLI)' -> 'Kichler Lighting'."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", raw_part_manuf).strip()


def trade_name(clean_name: str) -> str | None:
    return MANUFACTURER_TRADE_NAME.get(clean_name.lower())
