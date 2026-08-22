"""Thin client for a local Ollama server — the real AI in this pipeline.

No API key, no cloud dependency: `brew install ollama`, `ollama pull
<model>`, `ollama serve`. Uses stdlib only (no new dependency) since this is
a single JSON-mode HTTP call.
"""

import json
import os
import urllib.error
import urllib.request

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
TIMEOUT_SECONDS = 20


class OllamaUnavailable(Exception):
    """Raised when the local Ollama server can't be reached or errors out.
    Callers must catch this and fall back to the deterministic pipeline —
    the app must keep working with Ollama stopped, just less AI-assisted."""


def generate_json(prompt: str, system: str | None = None) -> dict:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.2},
    }
    if system:
        payload["system"] = system

    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise OllamaUnavailable(f"Could not reach Ollama at {OLLAMA_HOST}: {e}") from e

    raw = body.get("response", "")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise OllamaUnavailable(f"Ollama returned non-JSON output: {raw[:200]!r}") from e


def is_available() -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/version")
        with urllib.request.urlopen(req, timeout=2):
            return True
    except Exception:
        return False
