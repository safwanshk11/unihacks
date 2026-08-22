"""Batch-level de-duplication over a set of raw rows.

Two checks: exact MPN collisions, and near-identical descriptions (likely
the same item listed twice under slightly different text) via difflib
similarity. Both return {row_index: [messages]} so the caller can attach
validation flags after enrichment.
"""

import difflib

from app.models import RawProductIn

# Tuned against the real lighting-fixture data: many genuinely different
# SKUs (different finish codes) share near-identical generic description
# text ("Kichler Wall Light") and only differ in the MPN digits, which
# tripped this at 0.92 with zero true duplicates. 0.97 catches actual
# near-verbatim copies without flagging same-family/different-finish items.
NEAR_DUPLICATE_THRESHOLD = 0.97


def find_exact_duplicate_mpns(raw_items: list[RawProductIn]) -> dict[int, list[str]]:
    seen: dict[str, int] = {}
    flags: dict[int, list[str]] = {}
    for i, r in enumerate(raw_items):
        key = r.mfg_part_num.strip().lower()
        if key in seen:
            other = seen[key]
            flags.setdefault(i, []).append(f"Duplicate MPN — same part number as row {other}.")
            flags.setdefault(other, []).append(f"Duplicate MPN — same part number as row {i}.")
        else:
            seen[key] = i
    return flags


def find_near_duplicate_titles(
    raw_items: list[RawProductIn], threshold: float = NEAR_DUPLICATE_THRESHOLD
) -> dict[int, list[str]]:
    flags: dict[int, list[str]] = {}
    n = len(raw_items)
    for i in range(n):
        a = raw_items[i].part_desc.lower()
        for j in range(i + 1, n):
            if raw_items[i].mfg_part_num == raw_items[j].mfg_part_num:
                continue
            b = raw_items[j].part_desc.lower()
            ratio = difflib.SequenceMatcher(None, a, b).ratio()
            if ratio > threshold:
                flags.setdefault(i, []).append(
                    f"Near-duplicate description ({ratio:.0%} similar to {raw_items[j].mfg_part_num})."
                )
                flags.setdefault(j, []).append(
                    f"Near-duplicate description ({ratio:.0%} similar to {raw_items[i].mfg_part_num})."
                )
    return flags
