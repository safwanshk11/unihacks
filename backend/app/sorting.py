"""Sort logic shared by the catalog table (GET /api/products, sorted
client-side) and the CSV export (GET /api/products/export?sort=...),
so exporting matches whatever order is on screen. Mirrors
frontend/src/components/CatalogDashboard.tsx's sortProducts() — keep both in
sync if the ranking changes.
"""

from app.models import Confidence, EnrichedProduct

CONFIDENCE_RANK = {Confidence.low: 0, Confidence.medium: 1, Confidence.high: 2}
STATUS_RANK = {"pending": 0, "reviewed": 1}


def classpath_leaf(product: EnrichedProduct) -> str:
    return product.classpath.value.split(">")[-1].strip()


def overall_confidence_rank(product: EnrichedProduct) -> int:
    ranks = [CONFIDENCE_RANK[product.classpath.confidence]] + [
        CONFIDENCE_RANK[a.confidence] for a in product.attributes
    ]
    return min(ranks) if ranks else CONFIDENCE_RANK[Confidence.high]


def sort_products(
    products: list[EnrichedProduct], sort: str | None, direction: str
) -> list[EnrichedProduct]:
    if sort is None:
        return products
    reverse = direction == "desc"
    if sort == "classpath":
        return sorted(products, key=classpath_leaf, reverse=reverse)
    if sort == "confidence":
        return sorted(products, key=overall_confidence_rank, reverse=reverse)
    if sort == "status":
        return sorted(products, key=lambda p: STATUS_RANK.get(p.status, 0), reverse=reverse)
    return products
