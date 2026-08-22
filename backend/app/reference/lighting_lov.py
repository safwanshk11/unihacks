"""Candidate controlled vocabulary for lighting-fixture attributes.

PLACEHOLDER: hand-authored for this demo, not Unilog's real
Unicat_Lov_v1_0_Updated_With_Remarks.xlsx (161k rows, cross-category, not
available on this machine). This is the single biggest compliance gap in
the pipeline — real attribute values must come from that file, and
generating values outside it would score zero per the brief. Every value
this pipeline emits for an enumerated attribute is checked against these
lists and flagged non-compliant (not: wrong) when it falls outside them.
"""

FIXTURE_TYPE_LOV = {
    "Chandelier",
    "Pendant Light",
    "Wall Sconce",
    "Bath & Vanity Light",
    "Ceiling Light",
    "Downlight",
    "Flat Panel Light",
    "LED Strip Light",
    "LED Wrap Light",
    "Shop Light",
    "Highbay Light",
    "Post Light",
    "Work Light",
    "Flashlight",
    "LED Lamp",
    "HID Lamp",
    "Fluorescent Lamp",
    "Halogen Lamp",
    "Incandescent Lamp",
    "General Lighting Fixture",
}

FINISH_LOV = {
    "Black",
    "Distressed Black",
    "Brushed Nickel",
    "Chrome",
    "White",
    "Champagne Bronze",
    "Anvil Iron",
    "Not specified",
}

MOUNTING_TYPE_LOV = {
    "Wall Mount",
    "Ceiling Mount",
    "Suspended Mount",
    "Recessed Mount",
    "Surface Mount",
    "Post Mount",
    "Portable",
    "Handheld",
}

LIGHT_SOURCE_LOV = {
    "LED",
    "Fluorescent",
    "High Pressure Sodium",
    "Halogen",
    "Incandescent",
    "Not specified",
}

ATTRIBUTE_LOV = {
    "Fixture Type": FIXTURE_TYPE_LOV,
    "Finish": FINISH_LOV,
    "Mounting Type": MOUNTING_TYPE_LOV,
    "Light Source": LIGHT_SOURCE_LOV,
}


def is_lov_compliant(attribute_label: str, value: str) -> bool | None:
    """True/False if this attribute is enumerated; None if it's a measured
    value (dimension, wattage, CCT) with no fixed vocabulary to check."""
    lov = ATTRIBUTE_LOV.get(attribute_label)
    if lov is None:
        return None
    return value in lov
