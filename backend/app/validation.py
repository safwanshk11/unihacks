import re

from app.models import Confidence, EnrichedProduct, Severity, ValidationFlag

INVOICE_DESC_MAX = 40
MOBILE_DESC_RANGE = (60, 80)


def validate(product: EnrichedProduct) -> list[ValidationFlag]:
    """Rule-based validation over an enriched product: character-limit
    compliance, placeholder-LOV compliance, low-confidence attributes, and a
    data-quality check comparing the MPN embedded in the description against
    the record's own MPN (real data has cases where these don't match)."""
    flags: list[ValidationFlag] = []

    if len(product.invoice_desc.value) > INVOICE_DESC_MAX:
        flags.append(
            ValidationFlag(
                field="invoice_desc",
                issue=f"Exceeds the {INVOICE_DESC_MAX}-character limit ({len(product.invoice_desc.value)} chars).",
                severity=Severity.error,
            )
        )

    mobile_len = len(product.mobile_desc.value)
    if not (MOBILE_DESC_RANGE[0] <= mobile_len <= MOBILE_DESC_RANGE[1]):
        flags.append(
            ValidationFlag(
                field="mobile_desc",
                issue=f"Outside the {MOBILE_DESC_RANGE[0]}-{MOBILE_DESC_RANGE[1]} character target ({mobile_len} chars).",
                severity=Severity.warning,
            )
        )

    if product.classpath.confidence == Confidence.low:
        flags.append(
            ValidationFlag(
                field="classpath",
                issue="Fixture type could not be confidently classified from the description.",
                severity=Severity.warning,
            )
        )

    for attr in product.attributes:
        if attr.lov_compliant is False:
            flags.append(
                ValidationFlag(
                    field=f"attributes.{attr.label}",
                    issue=f"'{attr.value}' is not in the placeholder controlled vocabulary — verify against the real Unicat LOV.",
                    severity=Severity.warning,
                )
            )
        if attr.value.strip().lower() == "not specified":
            flags.append(
                ValidationFlag(
                    field=f"attributes.{attr.label}",
                    issue="Could not be determined from the input.",
                    severity=Severity.info,
                )
            )

    leading_token = re.match(r"^\S+", product.raw_part_desc)
    if leading_token and leading_token.group(0).lower() != product.raw_mfg_part_num.lower():
        flags.append(
            ValidationFlag(
                field="raw_part_desc",
                issue=(
                    f"Description starts with '{leading_token.group(0)}', which doesn't match this "
                    f"row's MPN ('{product.raw_mfg_part_num}') — possible data-entry inconsistency."
                ),
                severity=Severity.info,
            )
        )

    return flags
