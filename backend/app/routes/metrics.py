"""Self-computed QA metrics, standing in for field-level accuracy against
Unilog's real 200-item ground truth (not available on this machine). These
are the "show your evaluation" numbers the brief asks for, scoped to what we
can actually measure without that file: internal pipeline confidence and
compliance, not correctness against a known-good answer.
"""

from fastapi import APIRouter, Depends

from app.auth import require_session
from app.llm.llm_client import LLM_BACKEND, MODEL_NAME
from app.routes.products import AUTO_APPROVE_FIELD
from app.store import list_products
from app.validation import INVOICE_DESC_MAX, MOBILE_DESC_RANGE

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def _pct(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


@router.get("")
def get_metrics(_: str = Depends(require_session)):
    products = list_products()
    total = len(products)
    if total == 0:
        return {"total": 0}

    classification = {"high": 0, "medium": 0, "low": 0}
    for p in products:
        classification[p.classpath.confidence.value] += 1

    all_attrs = [a for p in products for a in p.attributes]
    attr_total = len(all_attrs)
    attr_from_input = sum(1 for a in all_attrs if a.source.value == "input")

    lov_checked = [a for a in all_attrs if a.lov_compliant is not None]
    lov_compliant = sum(1 for a in lov_checked if a.lov_compliant)

    invoice_ok = sum(1 for p in products if len(p.invoice_desc.value) <= INVOICE_DESC_MAX)
    mobile_ok = sum(
        1 for p in products if MOBILE_DESC_RANGE[0] <= len(p.mobile_desc.value) <= MOBILE_DESC_RANGE[1]
    )

    dedup_flags = sum(1 for p in products for f in p.validation_flags if f.field == "dedup")
    needs_review = sum(
        1 for p in products if any(f.severity.value in ("warning", "error") for f in p.validation_flags)
    )
    auto_approved = sum(1 for p in products for f in p.validation_flags if f.field == AUTO_APPROVE_FIELD)
    reviewed = sum(1 for p in products if p.status == "reviewed")

    llm_long_desc = sum(1 for p in products if p.long_desc.source.value == "llm")
    llm_classified = sum(1 for p in products if p.classpath.source.value == "llm")
    llm_unreachable = sum(1 for p in products for f in p.validation_flags if f.field == "llm")

    return {
        "total": total,
        "classification_confidence": classification,
        "attributes": {
            "total": attr_total,
            "from_input": attr_from_input,
            "from_input_pct": _pct(attr_from_input, attr_total),
        },
        "llm": {
            "backend": LLM_BACKEND,
            "model": MODEL_NAME,
            "long_desc_generated": llm_long_desc,
            "long_desc_generated_pct": _pct(llm_long_desc, total),
            "fallback_classifications": llm_classified,
            "llm_unreachable_count": llm_unreachable,
        },
        "lov_compliance": {
            "checked": len(lov_checked),
            "compliant": lov_compliant,
            "compliant_pct": _pct(lov_compliant, len(lov_checked)),
        },
        "char_limit_compliance": {
            "invoice_desc_ok_pct": _pct(invoice_ok, total),
            "mobile_desc_ok_pct": _pct(mobile_ok, total),
        },
        "dedup_flags": dedup_flags,
        "needs_review": needs_review,
        "needs_review_pct": _pct(needs_review, total),
        "review_status": {
            "reviewed": reviewed,
            "auto_approved": auto_approved,
            "manually_approved": reviewed - auto_approved,
            "pending": total - reviewed,
            "auto_approved_pct": _pct(auto_approved, total),
        },
    }
