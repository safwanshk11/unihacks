import os

from app.llm.base import EnrichmentProvider
from app.llm.hybrid_provider import HybridEnrichmentProvider


# LLM_PROVIDER selects the enrichment backend.
# - "hybrid" (default): the deterministic pipeline plus real local-LLM calls
#   (via Ollama) for low-confidence classification and grounded long-desc
#   generation. Falls back to pure rules automatically if Ollama isn't
#   running — see app/llm/ollama_client.py.
# To add a different LLM provider (e.g. Gemini): create a class in
# app/llm/ implementing EnrichmentProvider.enrich(), register it below, and
# set LLM_PROVIDER accordingly.
_PROVIDERS: dict[str, type[EnrichmentProvider]] = {
    "hybrid": HybridEnrichmentProvider,
}


def get_provider() -> EnrichmentProvider:
    name = os.environ.get("LLM_PROVIDER", "hybrid")
    provider_cls = _PROVIDERS.get(name)
    if provider_cls is None:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{name}'. Available: {', '.join(_PROVIDERS)}"
        )
    return provider_cls()
