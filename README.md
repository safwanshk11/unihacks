# Lumen

### Turn cryptic catalog rows into explainable product data

Industrial catalog feeds often arrive as rows like `3/8 CPLG BRS 150#`: useful
to a buyer who knows the trade, but not ready for a storefront, search index,
or downstream ERP. **Lumen** converts those rows into structured,
commerce-ready records and makes uncertainty visible instead of hiding it.

Built for the UniHack challenge, Lumen is a working product-enrichment console
with a deliberately measurable approach:

- **Classify** products into a useful taxonomy, across lighting and mixed catalogs.
- **Extract** attributes such as finish, bulb shape, CCT, wattage, dimensions, and UOM.
- **Normalize** manufacturer names, trade abbreviations, units, and fractions.
- **Describe** every product as invoice, mobile, short, and long copy.
- **Validate** character limits, duplicate rows, MPN mismatches, and vocabulary compliance.
- **Review** only low-confidence or flagged records, with source and rationale on every field.
- **Export** the exact 252-column Unilog Delivery Format.

## Why it is different

Lumen uses AI where language models help and rules where rules are safer.
Known product-code conventions are parsed deterministically, so a finish code
or dimension is auditable. The model handles open-ended classification and
writes grounded long descriptions from extracted facts, not from guesses.

The pipeline has two lanes:

```text
raw row
	-> shorthand expansion + manufacturer cleanup
	-> lighting specialist lane OR generic cross-category lane
	-> attributes + four descriptions + confidence + rationale
	-> validation + de-duplication
	-> auto-approve or send to human review
	-> 252-column Delivery Format
```

The specialist lane goes deep on lighting. The generic lane keeps a dishwasher,
pipe coupling, bolt, or glove from being forced into a lighting schema.

## See it in action

The dashboard supports the full workflow:

1. **Reseed** the 211-row lighting sample, or **Import file** with your own `.csv` or `.xlsx`.
2. Inspect the catalog sorted by classpath, confidence, or review status.
3. Open a record to see each value, its source (`input`, `inferred`, or `llm`), confidence, and rationale.
4. Edit flagged values in the review view and approve them.
5. Export CSV or JSON, or score the catalog against a known-good Delivery Format file.

Try the mixed-category fixture at
[`backend/app/data/sample_mixed_categories.csv`](backend/app/data/sample_mixed_categories.csv).

## Quick start

Requirements: Python 3.10+, Node.js 18+, npm, and macOS/Linux. Ollama is
optional but recommended for the default local AI path.

### 1. Start an LLM backend

```bash
brew install ollama
ollama pull llama3.2:3b
ollama serve
```

To use Gemini instead, copy `backend/.env.example` to `backend/.env` and set
`LLM_BACKEND=gemini` and `GEMINI_API_KEY`. The app falls back to deterministic
enrichment when the configured model is unavailable, with a visible validation
flag.

### 2. Start the API

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

API documentation: http://127.0.0.1:8001/docs

### 3. Start the console

```bash
cd frontend
npm install
npm run dev -- --port 5174
```

Open http://localhost:5174 and sign in with `admin` / `lumen-demo` for a local
demo. Change these values in `backend/.env` before sharing the app.

## API surface

The FastAPI service exposes the core workflow under `/api`:

| Endpoint | Purpose |
|---|---|
| `POST /api/auth/login` | Create a signed session |
| `GET /api/products` | List enriched records |
| `POST /api/products` | Enrich one raw product |
| `POST /api/products/batch` | Enrich a JSON batch |
| `POST /api/products/seed` | Load the bundled 211-row sample |
| `POST /api/products/upload` | Import CSV or XLSX and enrich it |
| `PATCH /api/products/{id}` | Save reviewer edits |
| `GET /api/products/export` | Export CSV or JSON |
| `GET /api/metrics` | Read internal QA and review metrics |
| `POST /api/products/evaluate` | Score against a Delivery Format file |

Interactive OpenAPI docs are available at `/docs` while the backend is running.
For backend configuration, provider details, and data contracts, see
[`backend/README.md`](backend/README.md).

## What is measured

After **Reseed**, the supplied run produced these reproducible operational
signals: 211 records enriched, 210 classified at high confidence, 83
auto-approved, 6 flagged for review, 99.0% vocabulary compliance, and 100%
invoice-description character-limit compliance. These are pipeline QA metrics,
not claims of ground-truth accuracy.

The repository includes two worked output examples, but not Unilog's full
200-item labeled ground truth. Lumen includes a scorer that can consume that
file when available and reports an attainable ceiling based on what appeared
in the raw input.

## Honest boundaries

The real reference pack was not available in this environment. The controlled
vocabulary, manufacturer lookup, and most UOM data in `backend/app/reference/`
are clearly marked, self-authored placeholders. Digital assets and manufacturer
source retrieval are intentionally out of scope. Empty output fields are left
empty rather than invented, and model values that cannot be traced to source
text are kept low-confidence and routed to review.

See the exact file-by-file breakdown in
[`backend/README.md`](backend/README.md#whats-real-vs-placeholder).

## Repository layout

```text
backend/app/llm/          Providers, specialist lane, generic lane, factory
backend/app/reference/    UOM, manufacturer, abbreviation, and LOV helpers
backend/app/routes/       Auth, products, and metrics endpoints
backend/app/schema/       Verbatim 252-column Delivery Format header contract
frontend/src/components/  Dashboard, review, import, evaluation, and login UI
reference_examples/       Worked Delivery Format examples
```

## Development checks

```bash
cd frontend
npm run build
npm run lint
```

The backend has no separate build step; run it with Uvicorn as shown above.

## Deploy on Render

The repository includes [`render.yaml`](render.yaml), which creates:

- a FastAPI web service for the backend,
- a static Vite site for the frontend,
- the API/frontend URL wiring and SPA fallback route.

In Render, choose **New → Blueprint** and connect this repository. Set the
requested secret values when prompted:

- `GEMINI_API_KEY` — a Gemini API key for cloud enrichment;
- `AUTH_PASSWORD` — the console password;
- `AUTH_SECRET` is generated automatically.

The Blueprint uses Gemini because Ollama is not available inside a normal
Render service. After deployment, open the static-site URL, sign in, and click
**Reseed** or import a catalog. The free tier does not provide persistent
disks, so the SQLite catalog can reset after a restart or deploy; reseed or
import the catalog again when that happens. For data that must survive
redeploys, attach a paid disk or move the store to Postgres. SQLite is
appropriate for this demo's single-service workload, not for multi-instance
production scaling.
