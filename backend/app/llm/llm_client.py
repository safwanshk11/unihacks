"""Picks which real LLM backend hybrid_provider.py talks to, via LLM_BACKEND:

  LLM_BACKEND=ollama (default) -> local Ollama, no API key, offline
  LLM_BACKEND=gemini           -> Google Gemini, needs GEMINI_API_KEY

hybrid_provider.py only imports from here — it doesn't know or care which
backend is actually behind generate_json()/is_available(), so switching
providers is a single env var, no code change.
"""

import os

LLM_BACKEND = os.environ.get("LLM_BACKEND", "ollama")

if LLM_BACKEND == "gemini":
    from app.llm.gemini_client import GEMINI_MODEL as MODEL_NAME
    from app.llm.gemini_client import GeminiUnavailable as LLMUnavailable
    from app.llm.gemini_client import generate_json, is_available
else:
    from app.llm.ollama_client import OLLAMA_MODEL as MODEL_NAME
    from app.llm.ollama_client import OllamaUnavailable as LLMUnavailable
    from app.llm.ollama_client import generate_json, is_available

__all__ = ["LLM_BACKEND", "MODEL_NAME", "LLMUnavailable", "generate_json", "is_available"]
