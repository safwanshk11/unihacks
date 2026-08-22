import io
import threading

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.dedup import find_exact_duplicate_mpns, find_near_duplicate_titles
from app.ingest import IngestError, parse_catalog
from app.llm.factory import get_provider
from app.models import Attribute, Confidence, EnrichedField, ProductPatch, RawProductIn, Severity, Source, ValidationFlag
from app.sample_data import SAMPLE_PRODUCTS
from app.schema.delivery_format import rows_to_csv
from app.sorting import CONFIDENCE_RANK, overall_confidence_rank, sort_products
from app.store import clear_products, get_product, insert_product, list_products, update_product
from app.validation import validate

router = APIRouter(prefix="/api/products", tags=["products"])

# Sync routes run in FastAPI's thread pool, so two /seed requests really can
# execute concurrently — each would clear_products() and re-insert 211 items
# independently, racing each other and leaving the DB with duplicated,
# interleaved data. This lock makes a second concurrent reseed fail fast
# with a clear error instead of silently corrupting the catalog.
_seed_lock = threading.Lock()

# Marks an auto-approval so it's distinguishable from a human clicking
# Approve — the review UI and GET /api/metrics both key off field=="status".
AUTO_APPROVE_FIELD = "status"
AUTO_APPROVE_NOTE = (
    "Auto-approved — no warning/error flags and every field is at least "
    "medium confidence (nothing the pipeline was genuinely guessing at)."
)


def _maybe_auto_approve(product) -> None:
    """Skip human review only when there's nothing to review: no rule
    violation (warning/error flag) and no field the pipeline itself flagged
    as a low-confidence guess. Medium confidence is fine — e.g. Mounting
    Type is always inferred from fixture type, never read directly, but
    that's a reasonable inference, not something uncertain enough to hold
    up for a person."""
    has_problem = any(f.severity in (Severity.warning, Severity.error) for f in product.validation_flags)
    has_low_confidence_field = overall_confidence_rank(product) == CONFIDENCE_RANK[Confidence.low]
    if has_problem or has_low_confidence_field:
        return
    product.status = "reviewed"
    product.validation_flags.append(ValidationFlag(field=AUTO_APPROVE_FIELD, issue=AUTO_APPROVE_NOTE, severity=Severity.info))


def _enrich_batch(raws: list[RawProductIn]):
    provider = get_provider()
    exact_dup_flags = find_exact_duplicate_mpns(raws)
    near_dup_flags = find_near_duplicate_titles(raws)

    products = []
    for i, raw in enumerate(raws):
        product = provider.enrich(raw)
        # provider.enrich() may have already appended flags of its own (e.g.
        # HybridEnrichmentProvider flags when Ollama isn't reachable) —
        # preserve those instead of overwriting with validate()'s output.
        product.validation_flags = product.validation_flags + validate(product)
        for msg in exact_dup_flags.get(i, []) + near_dup_flags.get(i, []):
            product.validation_flags.append(ValidationFlag(field="dedup", issue=msg, severity=Severity.warning))
        _maybe_auto_approve(product)
        products.append(insert_product(product))
    return products


@router.post("")
def create_product(raw: RawProductIn):
    return _enrich_batch([raw])[0]


@router.post("/batch")
def create_products_batch(raws: list[RawProductIn]):
    return _enrich_batch(raws)


@router.post("/seed")
def seed_products():
    if not _seed_lock.acquire(blocking=False):
        # Someone else's reseed is already running (another tab, or this one
        # after a reload). While the lock is held, clear_products() has
        # already run and every item since came only from that seed loop, so
        # the current row count *is* accurate in-progress completion —
        # enough for the frontend to show real progress instead of a dead-end
        # error, and to know when to stop watching.
        raise HTTPException(
            status_code=409,
            detail={
                "message": "A reseed is already in progress.",
                "done": len(list_products()),
                "total": len(SAMPLE_PRODUCTS),
            },
        )
    try:
        clear_products()
        return _enrich_batch(SAMPLE_PRODUCTS)
    finally:
        _seed_lock.release()


@router.get("")
def get_products():
    return list_products()


@router.post("/upload")
async def upload_catalog(file: UploadFile = File(...)):
    """Ingest a raw catalogue (CSV or XLSX) and enrich every row.

    This is the path the evaluation dataset takes — the pipeline is not
    bound to the sample file that ships in this repo.
    """
    if not _seed_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail={"message": "An import is already in progress.", "done": len(list_products()), "total": 0},
        )
    try:
        content = await file.read()
        try:
            raws = parse_catalog(file.filename or "", content)
        except IngestError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        clear_products()
        products = _enrich_batch(raws)
        return {"imported": len(products), "filename": file.filename}
    finally:
        _seed_lock.release()


@router.get("/export")
def export_products(format: str = "csv", sort: str | None = None, direction: str = "asc"):
    """Emit Unilog's Delivery Format — all 252 static headers, exact names,
    none added, renamed or removed."""
    products = sort_products(list_products(), sort, direction)

    if format == "json":
        return products

    buffer = io.StringIO()
    rows_to_csv(products, buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=unilog_delivery_format.csv"},
    )


@router.get("/{product_id}")
def get_product_detail(product_id: int):
    product = get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/{product_id}")
def patch_product(product_id: int, patch: ProductPatch):
    product = get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    def _edited(value: str) -> EnrichedField:
        return EnrichedField(
            value=value,
            confidence=Confidence.high,
            source=Source.input,
            rationale="Manually edited by reviewer.",
        )

    if patch.manufacturer_name is not None:
        product.manufacturer_name = _edited(patch.manufacturer_name)
    if patch.brand_name is not None:
        product.brand_name = _edited(patch.brand_name)
    if patch.classpath is not None:
        product.classpath = _edited(patch.classpath)
    if patch.invoice_desc is not None:
        product.invoice_desc = _edited(patch.invoice_desc)
    if patch.mobile_desc is not None:
        product.mobile_desc = _edited(patch.mobile_desc)
    if patch.short_desc is not None:
        product.short_desc = _edited(patch.short_desc)
    if patch.long_desc is not None:
        product.long_desc = _edited(patch.long_desc)
    if patch.attributes is not None:
        by_label = {a.label: a for a in product.attributes}
        for label, value in patch.attributes.items():
            existing = by_label.get(label)
            uom = existing.uom if existing else None
            product.attributes = [
                Attribute(
                    label=label,
                    value=value,
                    uom=uom,
                    confidence=Confidence.high,
                    source=Source.input,
                    rationale="Manually edited by reviewer.",
                    lov_compliant=existing.lov_compliant if existing else None,
                )
                if a.label == label
                else a
                for a in product.attributes
            ]
    if patch.status is not None:
        product.status = patch.status

    product.validation_flags = validate(product)
    update_product(product_id, product)
    return product
