# Lumen backend — Product Intelligence API

FastAPI service that enriches Unilog's raw catalogue rows — any category —
into structured, explainable, commerce-ready product data, and emits them in
the 252-column Delivery Format.

## Run

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

API docs: http://127.0.0.1:8001/docs

The frontend's Vite dev server proxies `/api` to `http://127.0.0.1:8001`, so run
the backend on port 8001 when developing locally (see `frontend/vite.config.ts`).

### The AI part

Enrichment defaults to the **hybrid** provider: the deterministic pipeline
below does the structured extraction, and a real LLM call handles the two
things regex can't — classifying items the keyword rules can't place, and
writing the long description as grounded prose instead of comma-joined
attributes. See [Hybrid AI layer](#hybrid-ai-layer) below for what that
actually does.

Two interchangeable backends for that LLM call, picked by `LLM_BACKEND` in
`backend/.env` (copy `backend/.env.example` to start):

**Ollama (default) — local, no API key, fully offline:**

```bash
brew install ollama
ollama serve &                # leave running in its own terminal/tab
ollama pull llama3.2:3b       # ~2GB, one-time
```

That's it — `LLM_BACKEND=ollama` is the default, nothing else to configure.
Runs at ~1s/item on Apple Silicon once the model is warm.

**Gemini — cloud, needs a free API key:**

1. Get a key at https://aistudio.google.com/apikey (free tier, no card
   required).
2. `cp backend/.env.example backend/.env`, then set:
   ```
   LLM_BACKEND=gemini
   GEMINI_API_KEY=your-key-here
   ```
   `backend/.env` is gitignored — the key never gets committed. Never put it
   directly in code or in a file that isn't gitignored.
3. Restart the backend so it picks up the `.env` (`app/main.py` loads it via
   `python-dotenv` before anything reads the environment).

Either way, if the configured backend isn't reachable — Ollama not running,
Gemini key missing/invalid/rate-limited — the app keeps working. It falls
back to the pure rule-based result per item and appends a visible `info`
validation flag saying so, rather than failing the request. Rows the specialist lane recognises (lighting) still enrich fully without a
model; rows that need the generic lane will be flagged for a human instead
of guessed at.

## Login

The console sits behind a session login. It is small but not decorative:
passwords are compared against a PBKDF2-SHA256 hash in constant time,
session tokens are HMAC-signed with a 12-hour expiry, and **no credential
is committed** — everything comes from `backend/.env` (gitignored).

```
AUTH_USERNAME=admin
AUTH_PASSWORD=lumen-demo     # change this before sharing
AUTH_SECRET=                 # random per process if unset; sessions end on restart
AUTH_DISABLED=0              # set 1 to bypass login for scripted runs
```

Every data route requires a valid session, including reads. The token lives
in `sessionStorage`, not `localStorage`, so it does not outlive the tab —
this console holds unpublished catalogue content.

## Scoring accuracy

`POST /api/products/evaluate` takes a known-good Delivery Format CSV and
returns field-level accuracy, joined on part number. The UI exposes it as
**Accuracy → Score against ground truth**. See `app/scoring.py`; it reports
an attainable-ceiling analysis alongside the raw score, because a bare
percentage invites the wrong conclusion when most of the ground truth was
never present in the input.

## The data

`app/data/lighting_input.csv` — 211 rows filtered from Unilog's real
`Unihack_ Sample Dataset - Input.csv` (the 1,000-row raw catalog), keeping
rows whose `Part_Manuf` is a lighting manufacturer (Kichler, Satco,
Phillips, Feit Electric, Streamlight). `app/sample_data.py` loads it — this
is what **Reseed from real data** in the UI seeds from.

`reference_examples/worked_examples_dishwashers.csv` (repo root) holds
Unilog's own 2 worked examples of the full 252-column target schema — used
to calibrate the description-building formulas (casing, `®` placement, UOM
spacing) even though they're a different category.

## Output contract — the 252-column Delivery Format

`GET /api/products/export?format=csv` emits Unilog's Delivery Format:
**all 252 static headers, exact names, none added, renamed or removed.**
The header list is not retyped — `app/schema/delivery_format.py` reads it
from a verbatim copy of the Expected Output header row
(`app/schema/delivery_format_headers.csv`), so it cannot drift.

Fields a 6-column raw input cannot supply (UPC, list price, image
filenames, country of origin, …) are emitted **empty rather than invented**.
The brief is explicit that fabricated values score zero and that reporting a
gap honestly is a strength.

## Ingesting the evaluation dataset

`POST /api/products/upload` accepts a **.csv or .xlsx** catalogue and
enriches every row — this is how the assessment dataset gets processed; the
pipeline is not bound to the sample that ships here. `app/ingest.py` is
deliberately tolerant of real spreadsheets:

- column names are matched loosely (case, spaces vs underscores, aliases
  like `MPN` / `Manufacturer Part Number` for `Mfg_Part_Num`),
- the header row is *located*, not assumed to be row 1, because the pack's
  own files carry title rows and merged cells above it,
- for XLSX, each sheet is tried until one looks like a product catalogue.

## What's real vs. placeholder

The brief describes a "rule book" and "master data" pack (content
guidelines, UOM standards, decimal/fraction table, a 27k-row manufacturer
list, a 161k-row cross-category LOV, category-specific LOV specs) that
wasn't available on this machine. Everything in `app/reference/` stands in
for one of those files — each module says so in its docstring:

| Module | Stands in for | Status |
|---|---|---|
| `reference/decimal_fraction.py` | `Decimal_Fraction.xlsx` | **Real** — computed arithmetic (1/64ths), not a placeholder |
| `reference/uom.py` | `Unilog_Master_UOM_Standards_Abbreviations_and_Terms.xlsx` | Placeholder — ~10 units this category needs, not the real ~500 |
| `reference/manufacturer_lookup.py` | `UniCat_Manufacturer_and_Brand_List.xlsx` | Placeholder — derived only from this dataset's own manufacturer strings |
| `reference/lighting_lov.py` | `Unicat_Lov_v1_0_Updated_With_Remarks.xlsx` | Placeholder — hand-authored candidate vocabulary; the biggest real compliance gap |

If the full pack becomes available, swap the contents of these modules for
real lookups against those files — nothing outside `app/reference/` needs
to change, since every caller goes through `is_lov_compliant()`,
`format_with_uom()`, `clean_manufacturer_name()` / `trade_name()`.

There's also no 200-item ground-truth file to score field-level accuracy
against — `GET /api/metrics` reports internal QA metrics instead
(classification confidence, LOV compliance, char-limit compliance, dedup
flags), not correctness against a known-good answer.

## Pipeline — two lanes, one router

`app/llm/hybrid_provider.py` routes every row:

**Common to all categories (deterministic):** manufacturer/brand
normalisation with placeholder filtering (`-- Unbranded --` → the
manufacturer trade name), UOM formatting, decimal→fraction, the four
description formulas with their character limits, validation, dedup and
auto-approval.

**Lane A — specialist (lighting).** `classify_lighting()` gets first
refusal. When it recognises a row, deterministic extractors pull finish
colour from MPN suffix codes (`45573BK` → Black), ANSI bulb shapes
(`A19`/`BR30`), CCT, wattage, lumens and dimensions. This is the depth the
brief asks for in "one category done fully."

Crucially, `classify_lighting()` returns **None** when it does not recognise
a row. It used to fall back to "General Lighting Fixture", which is how a
dishwasher once came out of this pipeline as a lighting fixture — with a
fluent LLM description written over the wrong facts, exactly the failure the
brief says scores zero.

**Lane B — generic (everything else).** `app/llm/generic_enrichment.py`
classifies with the model against a fixed department list and extracts
label/value/uom attributes. Two guards, both added after observed failures:

- **Trade shorthand is expanded first** (`app/reference/abbreviations.py`).
  `3/8 CPLG BRS 150#` classified as a *Hex Bolt* until it was expanded to
  `3/8 Coupling Brass 150 Pound Class`. This is the brief's own opening
  example of the problem, and it is the "input analysis" pipeline step.
- **Every extracted value must trace back to the source text.** A value the
  model returns that cannot be found in the input is kept at *low*
  confidence and flagged for a human — never silently accepted. This is what
  stops the model helpfully supplying a plausible-but-absent spec.

Accuracy on Lane B scales with the model: `llama3.2:3b` gets the item type
and sub-category right consistently but sometimes picks an imperfect
department. Switching `LLM_BACKEND=gemini` improves it without a code
change.

`app/dedup.py` runs separately, batch-wide, after enrichment: exact MPN
collisions plus near-verbatim description matches (tuned to 0.97 similarity
— a lower threshold flagged same-family/different-finish items as false
positives, since many Kichler rows share generic text and differ only in
the MPN).

`app/validation.py` also flags a real data-quality pattern found in this
dataset: rows where the MPN embedded in the free-text description doesn't
match the row's own `Mfg_Part_Num`.

## Auto-approval

`app/routes/products.py`'s `_maybe_auto_approve()` runs after every
enrichment (seed, batch, and single create). An item skips human review only
when there's nothing to review:

- **No warning/error validation flags** — no char-limit violation, no
  placeholder-LOV miss, no dedup hit, no MPN mismatch.
- **No field at "Low" confidence** — nothing the pipeline itself flagged as
  a genuine guess.

Medium confidence alone doesn't block it — e.g. Mounting Type is *always*
inferred from fixture type (never read directly from text), so requiring
every field to be "High" would auto-approve almost nothing (checked: 29/211
vs. 82/211 under the actual rule). Medium means "reasonably inferred," not
"uncertain" — only Low means that.

Auto-approved items get `status: "reviewed"` plus a distinct `info` flag
(`field: "status"`) explaining why, so the review UI can show "Auto-approved"
(a distinct color) instead of "Reviewed" (which still means a person clicked
Approve) — the human-in-the-loop signal stays visible even when a human
never touched the item. `GET /api/metrics`'s `review_status` block reports
`auto_approved` vs. `manually_approved` vs. `pending` separately.

## Hybrid AI layer

`app/llm/hybrid_provider.py` wraps the deterministic pipeline. Deliberately
*not* using an LLM for the structured extraction (finish codes, dimensions,
wattage) — regex against a known code convention is more accurate and more
auditable than asking a model to read digits off a part number, and the
brief is explicit that invented values score zero, so minimizing surface
area for hallucination on factual fields matters. The LLM is used for two
things a rules engine is structurally bad at:

- **Fallback classification** — when the keyword classifier finds nothing
  (low confidence), the raw description and manufacturer are sent to the
  model with the exact controlled fixture-type list, and it picks one. This
  reclassified `65-1222 1' Led Lt Multi CCT` from a low-confidence
  `General Lighting Fixture` fallback to `LED Lamp` — a genuine judgment
  call the keyword rules couldn't make.
- **Grounded long description** — the model is given only the already-
  extracted, already-validated attributes (`Manufacturer=Kichler Lighting;
  Brand=Kichler; Fixture Type=Wall Sconce; Finish=Black; ...`) and told to
  write one fluent sentence from *only* those facts. This is retrieval-
  grounded generation, not open-ended writing — it can't introduce a spec
  that wasn't extracted, because it never sees the raw text, only the
  structured facts.

Every LLM-touched field is tagged `source: "llm"` (distinct from
`source: "inferred"` for rule-based output) end to end — in the API
response, the review UI's field badges, and `GET /api/metrics`'s `llm`
block (which also reports which backend/model actually ran) — so it's
always visible which fields came from an actual model call versus a regex.

`app/llm/ollama_client.py` and `app/llm/gemini_client.py` are each a
~60-line stdlib HTTP client (no SDK, no new dependency beyond
`python-dotenv` for `.env` loading) exposing the same
`generate_json()` / `is_available()` shape. `app/llm/llm_client.py` picks
between them at import time based on `LLM_BACKEND`, so
`hybrid_provider.py` never imports either client directly — it only talks
to `llm_client`, and doesn't know or care which backend is actually behind
it.

## Adding a different LLM provider

Enrichment goes through `app/llm/base.py`'s `EnrichmentProvider` interface.
To add a third backend beyond Ollama/Gemini (OpenAI, Claude, etc.):

1. Create `app/llm/<name>_client.py` implementing the same shape as
   `ollama_client.py`: `generate_json(prompt, system) -> dict`,
   `is_available() -> bool`, and an `<Name>Unavailable` exception.
2. Add a branch for it in `app/llm/llm_client.py`'s `LLM_BACKEND` check.
3. Set `LLM_BACKEND=<name>` in `backend/.env`.

`hybrid_provider.py` and everything downstream of it needs no changes —
that's the point of routing everything through `llm_client.py`.

To bypass the hybrid pipeline entirely with a different *enrichment*
strategy (not just a different LLM backend for the same hybrid approach):
create a class implementing `EnrichmentProvider.enrich()`, register it in
`app/llm/factory.py`'s `_PROVIDERS` dict, and set `LLM_PROVIDER=<name>`.
