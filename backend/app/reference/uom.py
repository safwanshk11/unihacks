"""Approved unit-of-measure abbreviations.

PLACEHOLDER: a small hand-picked table covering only the units the lighting
category needs, not Unilog's real ~500-abbreviation
Unilog_Master_UOM_Standards_Abbreviations_and_Terms.xlsx (which was not
available on this machine). Swap APPROVED_UOM for that file's Sheet 1 when
it's available — the format function below doesn't need to change.
"""

APPROVED_UOM = {
    "in": "in",
    "inch": "in",
    "inches": "in",
    '"': "in",
    "ft": "ft",
    "foot": "ft",
    "feet": "ft",
    "'": "ft",
    "w": "W",
    "watt": "W",
    "watts": "W",
    "v": "V",
    "volt": "V",
    "volts": "V",
    "a": "A",
    "amp": "A",
    "amps": "A",
    "k": "K",
    "kelvin": "K",
    "lm": "lm",
    "lumen": "lm",
    "lumens": "lm",
    "hr": "hr",
    "hour": "hr",
    "hours": "hr",
}


def format_with_uom(value: str, unit_key: str) -> str:
    """'24' + 'in' -> '24 in' — a space always separates number and unit."""
    unit = APPROVED_UOM.get(unit_key.lower().strip(), unit_key)
    return f"{value} {unit}"
