"""Thin client for the Gemini API — the cloud alternative to local Ollama.
Same generate_json/is_available shape as ollama_client.py so hybrid_provider
(via llm_client.py) can't tell which one it's talking to.

Needs GEMINI_API_KEY (free tier at https://aistudio.google.com/apikey).
Loaded from backend/.env — see .env.example. Never hardcode the key here or
commit it; backend/.env is gitignored.
"""

import json
import os
import urllib.error
import urllib.request

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_HOST = "https://generativelanguage.googleapis.com"
TIMEOUT_SECONDS = 20


class GeminiUnavailable(Exception):
    """Raised when the Gemini API can't be reached, has no key configured, or
    errors out. Callers must catch this and fall back to the deterministic
    pipeline — the app must keep working without a Gemini key."""


def generate_json(prompt: str, system: str | None = None) -> dict:
    if not GEMINI_API_KEY:
        raise GeminiUnavailable("GEMINI_API_KEY is not set — add it to backend/.env (see .env.example).")

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}

    url = f"{GEMINI_HOST}/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise GeminiUnavailable(f"Gemini API error {e.code}: {e.read()[:300]!r}") from e
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise GeminiUnavailable(f"Could not reach Gemini API: {e}") from e

    try:
        text = body["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise GeminiUnavailable(f"Unexpected Gemini response shape: {str(body)[:300]}") from e


def is_available() -> bool:
    return bool(GEMINI_API_KEY)
