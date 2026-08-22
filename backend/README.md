# Backend — Product Intelligence API

FastAPI service that enriches Unilog's real raw catalog rows (lighting
fixtures & lamps slice) into structured, explainable, commerce-ready
product data.

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
validation flag saying so, rather than failing the request. Set
`LLM_PROVIDER=lighting` to skip the LLM entirely and always use the
deterministic-only pipeline (no `.env` needed at all in that mode).

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

## Pipeline

`app/llm/lighting_provider.py`, in order:

1. **Classify** — bulb/lamp vs. fixture (Phillips' catalog turned out to be
   almost entirely replacement bulbs, not fixtures — detected from ANSI
   shape codes like `A19`/`BR30` and base-type words, not guessed), then
   fixture/lamp type from description keywords.
2. **Extract attributes** — finish color from MPN suffix codes (`45573BK` →
   Black) or trailing description words, CCT/wattage/dimensions via regex,
   bulb shape/base/pack quantity for lamps.
3. **Normalize** — manufacturer/brand cleanup (placeholder-token filtering,
   trade-name lookup), UOM formatting, decimal→fraction for dimensions.
4. **Build descriptions** — invoice (≤40 char, CAPS), mobile (60–80 char,
   greedily padded with attributes to hit the target), short (title), long
   — all modeled on Unilog's own worked example.

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
