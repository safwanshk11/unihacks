"""Unilog's Delivery Format — the 252 static output headers.

The brief is explicit: "populate all the headers provided in the Expected
Output sheet. Do not modify, remove, or rename any of the headers." So the
header list is not retyped here — it is read from a verbatim copy of the
Expected Output header row (`delivery_format_headers.csv`), which makes
drift impossible.

Fields the pipeline cannot derive from a 6-column raw input (UPC, list
price, image filenames, country of origin, …) are emitted as empty strings
rather than invented. The brief is equally explicit that fabricated values
score zero, and that reporting a gap honestly is a strength.
"""

from __future__ import annotations

import csv
from pathlib import Path

from app.models import EnrichedProduct
from app.reference.uom import format_with_uom

_HEADERS_PATH = Path(__file__).parent / "delivery_format_headers.csv"

with open(_HEADERS_PATH, newline="", encoding="utf-8") as _f:
    DELIVERY_HEADERS: list[str] = next(csv.reader(_f))

# Attribute triplets run ATTRIBUTE_LABEL 1..50 / _VALUE / _UOM.
MAX_ATTRIBUTES = 50
MAX_FEATURES = 20


def _split_classpath(classpath: str) -> tuple[str, str, str]:
    """'A > B > C' -> ('A', 'B', 'C'), padded/truncated to Dept/Class/Fine."""
    parts = [p.strip() for p in classpath.split(">") if p.strip()]
    parts = (parts + ["", "", ""])[:3]
    return parts[0], parts[1], parts[2]


def to_delivery_row(product: EnrichedProduct) -> dict[str, str]:
    """Map one enriched product onto the 252-column Delivery Format."""
    row: dict[str, str] = {h: "" for h in DELIVERY_HEADERS}

    dept, klass, fine = _split_classpath(product.classpath.value)

    # --- identity, straight from the raw input -------------------------
    row["PART_NUMBER"] = product.raw_mfg_part_num
    row["Mfg_Part_Num"] = product.raw_mfg_part_num
    row["MANUFACTURER_PART_NUMBER"] = product.raw_mfg_part_num
    row["Part_Desc"] = product.raw_part_desc
    row["Part_Manuf"] = product.raw_part_manuf
    row["E1_Brand"] = product.raw_e1_brand or ""
    row["Unilog_Brand"] = product.raw_unilog_brand or ""
    row["DIB_Brand"] = product.raw_dib_brand or ""

    # --- normalised manufacturer / brand -------------------------------
    row["MANUFACTURER_NAME"] = product.manufacturer_name.value
    row["BRAND_NAME"] = product.brand_name.value

    # --- taxonomy ------------------------------------------------------
    row["Classpath"] = product.classpath.value
    row["Dept"] = dept
    row["Class"] = klass
    row["Fine"] = fine
    row["Product Name"] = product.item_type or fine

    # --- the description band ------------------------------------------
    row["INVOICE_DESC"] = product.invoice_desc.value
    row["MOBILE_DESC"] = product.mobile_desc.value
    row["SHORT_DESC"] = product.short_desc.value
    row["LONG_DESC1"] = product.long_desc.value

    # --- item features --------------------------------------------------
    for i, feature in enumerate(product.features[:MAX_FEATURES], start=1):
        row[f"ITEM_FEATURES_{i}"] = feature

    # --- attribute triplets ---------------------------------------------
    for i, attr in enumerate(product.attributes[:MAX_ATTRIBUTES], start=1):
        if not attr.value or attr.value == "Not specified":
            continue
        row[f"ATTRIBUTE_LABEL {i}"] = attr.label
        row[f"ATTRIBUTE_VALUE {i}"] = attr.value
        row[f"ATTRIBUTE_UOM {i}"] = attr.uom or ""

    # --- dimensions, promoted out of attributes where we found them -----
    for attr in product.attributes:
        label = attr.label.lower()
        if not attr.uom:
            continue
        if label in ("length", "overall length"):
            row["LENGTH"], row["LENGTH_UOM"] = attr.value, attr.uom
        elif label in ("width", "overall width"):
            row["WIDTH"], row["WIDTH_UOM"] = attr.value, attr.uom
        elif label in ("height", "overall height"):
            row["HEIGHT"], row["HEIGHT_UOM"] = attr.value, attr.uom
        elif label == "weight":
            row["WEIGHT"], row["WEIGHT_UOM"] = attr.value, attr.uom

    return row


def rows_to_csv(products: list[EnrichedProduct], buffer) -> None:
    writer = csv.DictWriter(buffer, fieldnames=DELIVERY_HEADERS, extrasaction="ignore")
    writer.writeheader()
    for p in products:
        writer.writerow(to_delivery_row(p))


def attribute_display(value: str, uom: str | None) -> str:
    return format_with_uom(value, uom) if uom else value
