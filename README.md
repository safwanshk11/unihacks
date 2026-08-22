# Lumen — AI-Powered Product Intelligence for Industrial Commerce

Named for the unit this pipeline actually deals in: lumens, Kelvin, watts —
real lighting-industry measurements extracted straight out of cryptic
distributor part numbers, not just a generic "light" pun.

Turns Unilog's real raw catalog rows — a manufacturer part number, a cryptic
abbreviated description, an unbranded flag — into structured, explainable,
commerce-ready product data: classified taxonomy, extracted attributes,
four description formats (invoice / mobile / short / long), confidence
scoring, source tracing (input vs. rule-inferred vs. a real local LLM call),
confidence-gated auto-approval, and validation flags for whatever's left for
human review.

A **hybrid pipeline**: deterministic regex/dictionary extraction handles the
structured fields (finish codes, dimensions, CCT — more auditable and less
hallucination-prone than asking a model to read digits off a part number),
and a real LLM call handles the two things a rules engine is genuinely bad
at — classifying items the keyword rules can't place, and writing the long
description as grounded prose from the already-extracted facts instead of
comma-joining them. That LLM call runs against either **Ollama** (local, no
API key, fully offline — the default) or **Gemini** (cloud, needs a free API
key), switchable with one env var — see
[The AI part](backend/README.md#the-ai-part) for setup and
[Hybrid AI layer](backend/README.md#hybrid-ai-layer) for exactly what's
rule-based vs. model-generated, and why.

Built for the UniHack challenge: *AI-Powered Product Intelligence for
Industrial Commerce* — scoped to the **lighting fixtures & lamps** slice of
Unilog's real 1,000-row sample dataset (211 rows: Kichler, Satco, Phillips,
Feit Electric, Streamlight), per the brief's own "depth beats breadth"
guidance rather than a shallow pass over the full catalog.

## What's real vs. placeholder

Only two of Unilog's reference files were available for this build: the
1,000-row raw catalog, and two worked examples of the target output schema
(not the full 200-item labelled ground truth). Everything the pipeline needs
beyond that — manufacturer normalization, the controlled attribute
vocabulary (LOV), UOM abbreviations — is **self-authored placeholder data**,
clearly flagged in code and in the UI, standing in for Unilog's real master
files until they're available. See
[backend/README.md](backend/README.md#whats-real-vs-placeholder) for the
exact file-by-file breakdown and what would replace each placeholder.

## Stack

- **Backend**: Python, FastAPI, SQLite — see [backend/README.md](backend/README.md)
- **Frontend**: React, Vite, TypeScript, Tailwind CSS

## Run locally

Two terminals:

```bash
# Terminal 0 — local LLM (once; leave running). Skip this and set
# LLM_BACKEND=gemini in backend/.env instead if you'd rather use a cloud
# key — see backend/README.md#the-ai-part.
brew install ollama && ollama pull llama3.2:3b
ollama serve
```

```bash
# Terminal 1 — backend (port 8001)
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

```bash
# Terminal 2 — frontend (port 5174, proxies /api to the backend)
cd frontend
npm install
npm run dev -- --port 5174
```

Open http://localhost:5174, click **Reseed from real data** to load the 211
real lighting rows, then open one to see the enrichment pipeline in action.

## How enrichment works

`backend/app/llm/lighting_provider.py` is the deterministic core: regex/
dictionary-driven classification (fixture vs. lamp/bulb, then fixture/lamp
type), attribute extraction (finish codes embedded in MPN suffixes, bulb
shape codes, CCT, wattage, dimensions), normalization (manufacturer/brand
cleanup, UOM formatting, decimal↔fraction conversion), and description
building (the real 4-tier invoice/mobile/short/long formula reverse-
engineered from Unilog's own worked example).

`backend/app/llm/hybrid_provider.py` (the default) wraps it with real local
LLM calls for fallback classification and grounded long-description
writing — see [backend/README.md](backend/README.md#hybrid-ai-layer). Falls
back to the pure deterministic result automatically if Ollama isn't
running, so the app never breaks with it stopped, just runs less
AI-assisted. Everything is built behind a swappable `EnrichmentProvider`
interface — a cloud model (Gemini, etc.) can replace Ollama without
touching the rest of the app.

Every generated field carries:
- **value** — the enriched content
- **confidence** — high / medium / low
- **source** — `input` / `inferred` (rule-based) / `llm` (a real model call)
- **rationale** — why the engine produced this value

Every enumerated attribute also carries **lov_compliant** — whether the
value falls inside the placeholder controlled vocabulary (not Unilog's real
Unicat LOV).

A rule-based validation layer (`backend/app/validation.py`) flags character-
limit violations, placeholder-LOV misses, and — notably — cases where the
MPN embedded in the description doesn't match the row's own MPN, a real
data-quality issue found in the raw catalog. Batch-level de-duplication
(`backend/app/dedup.py`) catches exact and near-verbatim duplicate rows.
A metrics endpoint (`GET /api/metrics`) surfaces self-computed QA numbers —
classification confidence, LOV compliance, char-limit compliance — standing
in for field-level accuracy since the real 200-item ground truth wasn't
available to score against.

Items with no validation flags and no low-confidence field skip human
review automatically (`status: "reviewed"`, tagged `Auto-approved` — not
just "Reviewed" — so it stays visible that no person looked at it); anything
else stays `Pending` for the review UI, where the catalog table sorts by
Classpath, Confidence, or Status.
