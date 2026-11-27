# 04 — Architecture · Hygisense (decoded)

> What runs today: `hygisense/` (Python) + `run_eval.py` + `prototype/app.html`. Data: BDPM files (real) + a simulated pharmacy.

## The pipeline, once a day per pharmacy

```text
 BDPM files (monthly)          pharmacy export (daily, per product, no patient data)
 drugs · generics · MITM       stock · units sold
 ANSM declarations
        │                              │
        ▼                              ▼
 [1] Ingest & join  ─────────────► [2] Demand forecast ──► days of stock left (range)
   rule · L4                          56-day mean · L3
        │
        ├──► [3a] ANSM declaration on this product, still inside the wholesaler window?  rule · L4
        │
        ├──► [3b] Vigilance index (8 weeks): ranks every product   relative risks + FDA · L3
        └──► [3c] Epidemic forecast (4 weeks): raises the reorder   Sentinelles · L3
                       │
                       ▼
             [4] Decision rule: BUY N / WATCH / NO / TOO LATE / FROZEN    rule · L2
                 cap 28 days · quota · network freeze · text never sets a quantity
                       │
                       ▼
             [5] Morning screen ──► ⊘ pharmacist ticks lines ──► draft order (copied, never sent)
                 + generics from the official register (rule · L1)
                 ⏻ switch: ON (L2) / SUGGEST-ONLY (L1) / OFF
```

## Components

| # | Component | Pattern | Rung | Trust level | Human checkpoint |
|---|---|---|---|---|---|
| 1 | Ingest BDPM, join with the pharmacy's products (CIS code) | prompt-chaining step, deterministic | 1 · rule | L4 | — (mismatches logged) |
| 2 | Demand forecast → days of stock left, with a range | — | 2 · classical (56-day mean; the seasonal version did not beat it) | L3 | — |
| 3a | "Declared by ANSM and still orderable" flag | routing on a rule | 1 · rule | L4 | — |
| 3b | Vigilance index, 8 weeks ahead (MITM, single lab, same molecule short, **US shortage**) | — | 2 · relative risks fitted on 2025 | L3, **WATCH only** | — |
| 3c | Epidemic forecast, 4 weeks (Sentinelles) → reorder × 1–1.4 on respiratory classes | — | 2 · log-linear | L3 | the pharmacist edits any quantity |
| 4 | Decision: quantity, cap, quota, freeze | rule | 1 · rule | **L2** | ⊘ **approval**: the pharmacist ticks each line |
| 5 | Generics fallback | rule on the official register | 1 | L1 | ⊘ the pharmacist decides any substitution |
| 6 | Free-text lab notices (COULD, not built) | augmented LLM | 3 | L2 | quote shown, never sets a quantity |
| 7 | Order | — | — | **human only** | ⊘ always: Hygisense never sends anything |

**Workflow, not agent.** The path is fixed and drawn in advance: ingest → forecast → flag/score → rule → screen. No model chooses a tool or a next step, and no model can set a quantity or place an order. Each step fails at a known place with a known fallback:

| Failure | Fallback | Coded in the MVP? |
|---|---|---|
| BDPM file missing or older than 35 days | banner "shortage data out of date", no BUY lines, WATCH only | no — spec |
| Pharmacy export missing today | yesterday's screen, greyed out, with its date | no — spec |
| Less than 14 days of sales | WATCH "not enough history", no quantity | yes (case C06) |
| Wholesaler already short | "TOO LATE", no quantity | yes (case C12, backtest) |
| Forecast = 0 | no quantity (spec v2: keep 2 boxes on a declaration) | yes |
| Risk model unavailable | rule 3a only: BUY lines keep working | by design (3a does not use the model) |

## Human checkpoints and the override switch

- **⊘ Approval: every BUY line.** The pharmacist ticks it and exports the draft into their usual software. Owner on our side: **Yannick (PM)** for the quality of the recommendations.
- **⊘ Abstention: the screen withdraws.** It shows no BUY on a product already short at the wholesaler ("too late"), on a product under network freeze, or when the data is stale.
- **⏻ Override switch, three positions:** **ON** (L2, lines can be ticked) → **SUGGEST-ONLY** (L1, lines shown, nothing can go into the draft) → **OFF** (screen paused, "order as usual"). It is a feature flag per pharmacy and for the whole network. **Owner: Nissrine (Head of Operations)**, with Tom (engineer on call) at night. Each pharmacist also has their own switch for their pharmacy. Test: see 06_07_experiments_operations.md §4.

## What the eval says about this architecture (evals/report_v0.md)

- Rule 3a decides the purchases: 63.5 % of the shortages that would have emptied a shelf were anticipated, 0 buys above the cap.
- Index 3b (AUC 0.76; the logistic regression v1 reached 0.68) sees 28 % of the next 8 weeks' declarations in its top 10 %: good enough to watch, not to buy.
- Forecast 3c beats persistence and climatology by 9–11 %.
- Demand: the 56-day mean beat the seasonal version (WAPE 38 % vs 42 %), so we kept the simpler one.

## Stack

Python 3.11 · pandas · scikit-learn · no LLM in the MVP · `prototype/app.html` is one static page built by `build_app.py` from the pipeline outputs, so it opens with a double-click. **Connection to the pharmacy software (LGO):** read-only nightly extract of stock and sales (an agent in the pharmacy, or the editor's API when there is one); the order goes back as a file the LGO imports, and the LGO sends it through PharmaML. Production surface (not built): the same `hygisense/` package behind a FastAPI `/recommendations` endpoint, called once a night per pharmacy, with traces in Langfuse (06_07 §3).
