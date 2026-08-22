"""Field-level accuracy against a known-good Delivery Format file.

The brief: "Field-level accuracy against the 200 known-good rows,
character-limit compliance, and percentage of values found in the LOV are
all simple, credible metrics. Judges will look for them."

This scores whatever ground truth it is handed — the 2-row worked example
that ships here, or the full 200-item file the moment it is available. Rows
are joined on the manufacturer part number, so the two files need not be in
the same order.

Three grades per field, because "wrong" and "differently formatted" are not
the same failure and lumping them together would flatter the result:
  exact      — byte-identical after whitespace trim
  normalised — same content, different case/punctuation/spacing
  miss       — genuinely different
Fields blank in the ground truth are skipped, not counted as wins.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field

from app.models import EnrichedProduct
from app.schema.delivery_format import to_delivery_row

# The columns this pipeline actually claims to populate. Scoring the other
# ~230 (UPC, list price, image URLs) would mostly measure blank-vs-blank.
SCORED_FIELDS = [
    "MANUFACTURER_NAME",
    "BRAND_NAME",
    "Classpath",
    "Dept",
    "Class",
    "Fine",
    "Product Name",
    "INVOICE_DESC",
    "MOBILE_DESC",
    "SHORT_DESC",
    "LONG_DESC1",
]

CHAR_LIMITS = {"INVOICE_DESC": (None, 40), "MOBILE_DESC": (60, 80)}


def _normalise(value: str) -> str:
    """Collapse the differences that are formatting rather than meaning."""
    text = value.lower().strip()
    text = text.replace("®", "").replace("™", "")
    text = re.sub(r"\s*>\s*", ">", text)  # 'A > B' vs 'A>B'
    text = re.sub(r"[^a-z0-9>]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class FieldScore:
    exact: int = 0
    normalised: int = 0
    miss: int = 0
    examples: list[dict] = field(default_factory=list)

    @property
    def compared(self) -> int:
        return self.exact + self.normalised + self.miss

    def as_dict(self) -> dict:
        total = self.compared or 1
        return {
            "compared": self.compared,
            "exact": self.exact,
            "normalised_match": self.normalised,
            "miss": self.miss,
            "exact_pct": round(100 * self.exact / total, 1),
            "any_match_pct": round(100 * (self.exact + self.normalised) / total, 1),
            "examples": self.examples[:3],
        }


def load_ground_truth(content: bytes) -> dict[str, dict[str, str]]:
    """Keyed by manufacturer part number."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    rows = list(csv.DictReader(io.StringIO(text)))
    truth: dict[str, dict[str, str]] = {}
    for row in rows:
        key = (row.get("Mfg_Part_Num") or row.get("PART_NUMBER") or row.get("MANUFACTURER_PART_NUMBER") or "").strip()
        if key:
            truth[key.lower()] = row
    return truth


def score(products: list[EnrichedProduct], truth: dict[str, dict[str, str]]) -> dict:
    scores: dict[str, FieldScore] = {f: FieldScore() for f in SCORED_FIELDS}
    matched, unmatched = 0, []

    for product in products:
        key = product.raw_mfg_part_num.strip().lower()
        expected = truth.get(key)
        if expected is None:
            unmatched.append(product.raw_mfg_part_num)
            continue
        matched += 1
        ours = to_delivery_row(product)

        for name in SCORED_FIELDS:
            want = (expected.get(name) or "").strip()
            if not want:
                continue  # blank in ground truth — nothing to score against
            got = (ours.get(name) or "").strip()
            bucket = scores[name]
            if got == want:
                bucket.exact += 1
            elif got and _normalise(got) == _normalise(want):
                bucket.normalised += 1
            else:
                bucket.miss += 1
                bucket.examples.append({"mpn": product.raw_mfg_part_num, "expected": want[:160], "got": got[:160]})

    # Character-limit compliance is measurable without any ground truth.
    limits: dict[str, dict] = {}
    for name, (low, high) in CHAR_LIMITS.items():
        ok = 0
        for p in products:
            value = to_delivery_row(p).get(name) or ""
            length = len(value)
            if (low is None or length >= low) and (high is None or length <= high):
                ok += 1
        limits[name] = {
            "within_limit": ok,
            "of": len(products),
            "pct": round(100 * ok / len(products), 1) if products else 0.0,
        }

    compared = sum(s.compared for s in scores.values())
    exact = sum(s.exact for s in scores.values())
    any_match = exact + sum(s.normalised for s in scores.values())

    return {
        "rows_scored": matched,
        "rows_in_ground_truth": len(truth),
        "rows_not_in_ground_truth": len(unmatched),
        "overall": {
            "fields_compared": compared,
            "exact_pct": round(100 * exact / compared, 1) if compared else 0.0,
            "any_match_pct": round(100 * any_match / compared, 1) if compared else 0.0,
        },
        "by_field": {name: s.as_dict() for name, s in scores.items()},
        "char_limit_compliance": limits,
        "attainable_ceiling": attainable_ceiling(products, truth),
    }


def attainable_ceiling(products: list[EnrichedProduct], truth: dict[str, dict[str, str]]) -> dict:
    """How much of the ground truth is even *reachable* from the input?

    A raw score alone is misleading. Measured on the worked examples, 0 of
    11 ground-truth attributes appear anywhere in the input string — they
    were sourced from the manufacturer's own site (see the MFR URL column),
    which is pipeline step 5, "enrichment from manufacturer sources".

    Separating "we got this wrong" from "this was never in the input" is the
    difference between a bug and a scope boundary, and it tells you exactly
    where the remaining accuracy lives.
    """
    in_input = 0
    external = 0
    external_examples: list[str] = []

    for product in products:
        expected = truth.get(product.raw_mfg_part_num.strip().lower())
        if expected is None:
            continue
        haystack = _normalise(f"{product.raw_mfg_part_num} {product.raw_part_desc} {product.raw_part_manuf}")
        for i in range(1, 51):
            label = (expected.get(f"ATTRIBUTE_LABEL {i}") or "").strip()
            value = (expected.get(f"ATTRIBUTE_VALUE {i}") or "").strip()
            if not label or not value:
                continue
            core = _normalise(value)[:8]
            if core and core in haystack:
                in_input += 1
            else:
                external += 1
                if len(external_examples) < 6:
                    external_examples.append(f"{label} = {value[:40]}")

    total = in_input + external
    return {
        "ground_truth_attributes": total,
        "present_in_raw_input": in_input,
        "requires_manufacturer_source": external,
        "reachable_pct": round(100 * in_input / total, 1) if total else 0.0,
        "note": (
            "Attributes absent from the raw input cannot be derived without pipeline step 5 "
            "(enrichment from manufacturer sources). This is a scope boundary, not a defect."
        ),
        "examples_requiring_external_source": external_examples,
    }
