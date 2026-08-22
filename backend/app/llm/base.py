from abc import ABC, abstractmethod

from app.models import EnrichedProduct, RawProductIn


class EnrichmentProvider(ABC):
    """Turns a sparse RawProductIn into a structured, explainable EnrichedProduct.

    To add a real LLM provider (Gemini, Ollama, ...): implement `enrich` against
    this same interface, register it in `app/llm/factory.py`, and select it via
    the LLM_PROVIDER env var. Every output field must carry confidence/source/
    rationale so the rest of the app (validation, review UI) keeps working
    unchanged.
    """

    @abstractmethod
    def enrich(self, raw: RawProductIn) -> EnrichedProduct: ...
