# Lumen — deck source material

Everything needed to build the UniHack slides. Every number here was
measured on this machine and is reproducible by the command shown; nothing
is estimated. Where a number is unflattering it is still here, because the
strongest part of this submission is the measurement, not the score.

---

## 1. The one-line pitch

> Industrial distributors hand over catalogue rows like `3/8 CPLG BRS 150#`.
> Lumen turns them into commerce-ready records — classified, attributed,
> described four ways, and scored — and tells you exactly which ones a human
> still needs to look at.

---

## 2. The problem (slide 1–2)

Raw distributor data is unusable as shipped:

| Symptom | Real example from the dataset |
|---|---|
| Cryptic shorthand | `3/8 CPLG BRS 150#` |
| Brand field empty | `-- Unbranded --` on 1,000 of 1,000 rows |
| Supplier ≠ manufacturer | `Appliance Dealers Cooperative (APPDE)` for a Whirlpool dishwasher |
| Data-entry drift | Row MPN `55226BKLFU`, description says `55226BKFLU` |

That last one is a real defect Lumen found in Unilog's own sample data —
two letters transposed. Good slide moment.

---

## 3. What it does (slide 3)

Six of the brief's eight pipeline steps:

1. **Input analysis** — trade-abbreviation glossary
2. **De-duplication** — exact MPN + near-verbatim description
3. **Taxonomy & classification** — two-lane router
4. **Attribute extraction** — specialist regex + verified model extraction
5. **Cleansing & normalisation** — manufacturer/brand, UOM, decimal→fraction
6. **Description building** — invoice / mobile / title / long, char-limited

Not attempted, deliberately: *enrichment from manufacturer sources* and
*digital assets*. Section 8 explains why that is the most interesting slide
in the deck.

---

## 4. Architecture (slide 4 — the diagram slide)

```
                     raw row (any category)
                              │
                   manufacturer / brand resolution
                              │
                    ┌─────────┴─────────┐
        specialist  │                   │  generic
     (lighting)     │                   │  (everything else)
                    ▼                   ▼
      finish codes from MPN      LLM classify vs fixed
      ANSI bulb shapes           department list
      CCT / wattage / lumens     LLM extract, then verify
                    └─────────┬─────────┘
                              ▼
        UOM · decimal→fraction · 4 descriptions · validation
                              ▼
              auto-approve  or  route to a human
                              ▼
                  252-column Delivery Format
```

**The point of the fork:** the specialist lane returns *nothing* when it
doesn't recognise a row. An earlier build had it claim everything, and a
dishwasher came out as a "General Lighting Fixture" with fluent LLM prose
written over the wrong facts — exactly what the brief says scores zero.

---

## 5. Where the AI actually sits (slide 5)

Deliberately **not** used for reading specs off a part number — regex
against a known code convention is more accurate and auditable there. The
model does the three things rules cannot:

| Job | Why a model |
|---|---|
| Classify an open catalogue | A keyword table cannot cover dishwashers, faucets, fittings and bolts |
| Identify the real manufacturer | `WDTS7024RZ` → Whirlpool, which no rule could know |
| Write the long description | Grounded in already-extracted facts, never the raw text |

Two guardrails worth a slide:

- **Grounding.** The description model only ever sees extracted attributes,
  never the raw string, so it cannot introduce a spec that was not extracted.
- **Traceability.** Any value the model proposes that cannot be found in the
  source text is kept at *low* confidence and routed to a human — never
  silently accepted.

Runs on **local Ollama** (no API key, works offline) or **Gemini**, switched
by one env var.

---

## 6. Results (slide 6 — the numbers slide)

Reproduce: `GET /api/metrics` after **Reseed**.

| Metric | Value |
|---|---|
| Records enriched | **211** |
| Classified at high confidence | **210 / 211** |
| Auto-approved, no human needed | **83 (39.3%)** |
| Flagged for review | **6 (2.8%)** |
| Attributes read from input, not inferred | **56.8%** |
| Values inside the controlled vocabulary | **99.0%** |
| Invoice description ≤ 40 chars | **100%** |
| Mobile description in 60–80 chars | **69.2%** |
| Descriptions written by the model | **211 / 211** |

Do not hide the 69.2%. It is honest: those rows genuinely lack enough input
attributes to fill a 60-character line, and padding them with a repeated
manufacturer name would have gamed the metric rather than improved the data.

**Model choice measurably matters** — 12 random non-lighting rows from the
real 1,000-row file, scored on department:

| Model | Correct |
|---|---|
| `llama3.2:3b` | ~9 / 12 — filed a cordless ratchet under *Fasteners*, heated gloves under *Lighting* |
| `qwen2.5:7b` | ~11 / 12 — got both right |

---

## 7. Output contract (slide 7)

- Exports **all 252 static Delivery Format headers**, exact names, none
  added, renamed or removed. Verified programmatically: `ref == ours → True`.
- Fields a 6-column input cannot supply are left **empty, not invented**.
- Accepts **`.csv` or `.xlsx`**; the header row is *located*, not assumed,
  because the pack's own sheets carry title rows and merged cells above it.

---

## 8. The finding — put this near the end and let it land

Built a scorer against the known-good Delivery Format file. First run: **9.1%**
exact. It immediately caught four real bugs:

- `INVOICE_DESC` read `DISHWASHER DISHWASHER`
- `MOBILE_DESC` repeated the company name twice
- Classpath used `" > "` where ground truth uses `">"`
- **Supplier was being used as the manufacturer** — one wrong value
  propagating into five fields

After fixes: **12.5%**. Then the scorer answered the more important question:

> **0 of 92 ground-truth attributes appear anywhere in the raw input.**

Series, voltage, amperage, sound level, dimensions — every one came from the
manufacturer's own site. The ground-truth file even carries a `MFR URL`
column pointing at `learnwhirlpool.com`.

**So 12.5% is not "we are bad." It is near the ceiling for any pipeline that
does not retrieve.** The remaining accuracy lives entirely behind step 5,
and we can prove it rather than assert it.

That reframes the whole submission: *we measured exactly where the value is,
and it is behind the one step we scoped out.* The brief itself says two or
three steps done convincingly **with evidence** beats a shallow pass at
everything.

---

## 9. Live demo script (5 minutes)

1. **Sign in** — `admin` / `lumen-demo`. Note: PBKDF2-hashed, HMAC-signed
   sessions, no credential in the repo.
2. **Dashboard** — hero shows one real cryptic string becoming a full
   record. Point at the readout: 211 records, 83 auto-approved, 6 flagged.
3. **Open a flagged row** — show source and confidence on *every* field, and
   the rationale line explaining why each value exists.
4. **Show the MPN-mismatch flag** — a real defect found in Unilog's data.
5. **Import file** → `backend/app/data/sample_mixed_categories.csv` — proves
   it is not a lighting-only demo. Decking, dryers, trimmers, gloves.
6. **Export CSV** — open it, scroll sideways, 252 headers.
7. **Accuracy → Score against ground truth** — land section 8.

Reseeding runs a real model call per row (~4 min for 211). **Seed before you
present**, and use *Import file* live instead.

---

## 10. Honest gaps — own them on a slide, don't get caught by them

| Gap | Position |
|---|---|
| No 200-item ground truth available | Harness already scores it unchanged the moment it arrives |
| Steps 5 & 8 not attempted | Deliberate scope; section 8 proves where the value is |
| Controlled vocabulary is self-authored | Real LOV/manufacturer/UOM files were not in the pack |
| Department accuracy ~11/12 | Measured, not guessed; improves with a larger model |

Judges respect a measured limitation far more than an unmeasured claim.

---

## 11. Suggested slide order

1. Title — *Lumen: cryptic part numbers, made commerce-ready*
2. The problem, with the four real examples
3. What it does — the six pipeline steps
4. Architecture — the two-lane diagram
5. Where the AI sits + the two guardrails
6. Results — the numbers table
7. Output contract — 252 headers, any file in
8. **The finding** — 0 of 92, and what it means
9. Honest gaps
10. Live demo
