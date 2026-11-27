# spec.md — Hygisense MVP (v2, after the S4 evaluation)

> v1 (S3) → v2 (19 Nov 2026): every line marked **[v2]** comes from a number in `evals/report_v0.md`.

## Problem
Pharmacies learn about drug shortages when the shelf is empty and the wholesaler can no longer deliver; DP-Ruptures fires 72 h after their order failed. Hygisense acts **while the product can still be ordered**. Every morning, for every product, it checks the ANSM declarations against the pharmacy's own stock and sales, and recommends **buying N boxes ahead now, or not**. The pharmacist validates every line, and Hygisense never sends an order.

**[v2] What changed after the evaluation.** v1 bet on a logistic regression to predict a lab declaration 8 weeks ahead; on real 2026 data it did not beat "is it a MITM?" (AUC 0.68). v2 splits the job: (1) a **rule** buys on the day ANSM publishes a *tension* or *rupture*, within the two weeks wholesalers must still deliver (art. R5124-59 CSP), which anticipates **63.5 %** of the shortages that would have emptied the shelf; (2) a **vigilance index** (relative risks incl. *already short in the US*, FDA) ranks every product before any alert, AUC 0.76, and its top 10 % holds 28 % of the next 8 weeks' declarations; (3) an **epidemic forecast** (Sentinelles, 4 weeks) raises the normal reorder of respiratory and anti-infective products.

## Workflow (inputs → outputs)

| # | Step | Input | Output | Rung | Trust |
|---|---|---|---|---|---|
| 1 | Ingest public data | BDPM files (monthly): drugs, boxes, generic groups, compositions, MITM, **ANSM availability** | `products`, `events(product, status, start, end)` | 1 rule | L4 |
| 2 | Demand forecast | daily units sold per product (pharmacy export) | `demand` = 56-day mean, `days_left` with a range | 2 classical | L3 |
| 3a | **[v2] Declared and still orderable** | events, today | `declared = start ≤ today < start + 14 days` | 1 rule | L4 |
| 3b | **[v2] Vigilance index** (8 weeks) | MITM, single lab, same molecule short elsewhere, **US shortage (openFDA)**, ATC class | `index` (×N vs average) + `risk_8w` + reasons | 2 relative risks fitted on 2025 | L3 — **WATCH only** |
| 3c | **[v2] Epidemic forecast** | Réseau Sentinelles weekly incidence (flu, acute respiratory infections) | incidence in 4 weeks → reorder × (1 to 1.4) on respiratory / anti-infective / analgesic | 2 log-linear | L3 |
| 4 | Decision | days_left, demand, risk, declared, quota, freeze | BUY / WATCH / NO / TOO LATE / FROZEN, `buy_qty` | 1 rule | L2 |
| 5 | Generics fallback | product, generic register | substitutable products from the same group | 1 rule | L1 |
| 6 | Notices (COULD, not built) | notice text | `return_date` + quote | 3 LLM | L2 |
| 7 | Morning screen | 2–5 | BUY lines first, then TOO LATE (5 shown), then WATCH; draft order the pharmacist ticks | — | — |

## Decision rule (step 4) — `hygisense/decide.py`

```text
NORMAL_COVER = 14 days ; EXTRA_COVER = 28 days (cap) ; BUY = 0.50 ; WATCH = top 10 % of the vigilance index (2025)
risk = 0.95 if declared else risk_8w (vigilance)            # [v2] the declaration is the trigger

if network_freeze:                         FROZEN, 0
elif wholesaler already short (fill < 1):  TOO LATE, 0        # [v2] nothing to buy any more
elif history < 14 days:                    WATCH "not enough history", 0
elif risk >= BUY:
    qty = min(ceil(demand × 42 − stock), floor(demand × 28), quota)
    BUY qty if qty > 0 else NO "enough stock"
elif risk >= WATCH:                        WATCH, 0
else:                                      NO "normal reorder", 0
```

**[v2] Next changes, one per miss (not coded yet, re-run the eval after each):**
1. Slow movers (**all 19 misses**, ≤ 2 boxes a month): on a declaration, keep at least **2 boxes** of any product sold in the last 6 months.
2. Useless buy-aheads (26–33 %, within target): on a **tension**, buy only if the shelf empties within 8 weeks at 40 % delivery. On a **rupture**, keep the rule.
3. A product already under an older declaration: label it "already short" and count it apart in the report.

## Contract

```text
Recommendation {
  product_id: str (CIS) ; name: str ; holder: str
  decision: "BUY" | "WATCH" | "NO" | "TOO LATE" | "FROZEN"
  buy_qty: int                 # never above the cap (28 days of demand) or a quota
  days_left: float | null ; days_left_range: [float, float] | null
  risk_8w: float               # 0.95 when declared by ANSM
  reasons: [str]               # e.g. "ANSM: tension declared on 01/09/2026" + link
  ansm_link: str | null
  generics: [{product, in_stock_units}]   # [] → "no substitutable generic in the register"
}
```

## Guardrails (hard-coded — the models are not trusted with these)
1. **No order is ever sent by the tool.** The draft is copied into the pharmacist's own software.
2. **Anti-hoarding cap:** buy-ahead ≤ 28 days of forecast demand and ≤ any ANSM or wholesaler quota. A **network freeze** per product stops all buy-aheads when too many pharmacies buy at once (06_07 §3, threshold).
3. **Generics only from the official register**; never another molecule.
4. **No patient data**: the pharmacy export is aggregated per product per day before it leaves the pharmacy.
5. **Text cannot change a quantity or trigger an action** (case C17).
6. Risk per presentation (CIS), not per molecule (case C10).

## Evaluation — `python run_eval.py`
- **Decision cases:** `evals/cases_v0.csv`, 20/20 must pass.
- **Backtest:** real ANSM declarations 2026 × two simulated pharmacies. A shortage counts if it would have emptied the shelf; it is anticipated if Hygisense said BUY at least 7 days before empty, while the wholesaler could still deliver.
- **Risk model:** time split, train 2024 – Mar 2025, validation Apr – Nov 2025 (threshold), test 2026 once.

## Done (success criterion) — status 19 Nov 2026
| Criterion | v0 result |
|---|---|
| Anticipation ≥ 25 % on the backtest | **63.5 %** ✅ (at the ANSM alert) · plus 28 % of declarations seen 8 weeks ahead by the vigilance index |
| 0 recommendation above the cap or a quota | **0** ✅ |
| 20/20 decision cases | **20/20** ✅ |
| Counter-metric: useless buy-aheads, tracked, target < 40 % | 29 % ✅ |

## Next: the network (V2, designed, not built)
More pharmacies must mean **better-placed** buying, not **more** buying: otherwise our own pharmacies would drain wholesalers and create the shortage we predict.

| Piece | What it does | Rule that keeps it safe |
|---|---|---|
| **Network cap, pro rata** | On one product, all buy-aheads proposed across our pharmacies on one day are capped at 25 % of their normal 2-week demand, **split pro rata to each pharmacy's normal sales** (not first come, first served) | already the network freeze threshold (06_07 §3); the split is new |
| **Local epidemic map** | Aggregated sales of respiratory / anti-infective classes by zone show where an epidemic starts; the reorder boost applies only where it rises | aggregated only, a zone is shown only with ≥ 5 pharmacies; no pharmacy ever sees another's figures; no patient field |
| **Early supply signal** | Orders failing at wholesalers in many pharmacies at once = a shortage before it is declared | shared upstream (lab, wholesaler, ANSM) as a count, never as one pharmacy's data |
| **Spill-over check** | Wholesaler service rate for pharmacies **without** Hygisense, read on the 5 % holdout and one partner wholesaler | if it falls, network freeze on the products concerned |

Until the network is dense enough (≥ 5 pharmacies per zone), the regional Sentinelles series plays the role of the local map. Existing players (OpenHealth, IQVIA panels used by ANSM's winter plan) already map epidemics from pharmacy sales; our difference is turning the local signal into each pharmacy's order quantity, capped.

## Out of scope (WON'T)
Sending orders · other molecules as alternatives · messages to patients · showing one pharmacy's data to another · hospital pharmacies · negotiating with wholesalers · an LLM in the MVP.

## Stack
Python, pandas, scikit-learn. Sources: BDPM, openFDA, Réseau Sentinelles (`hygisense/signals.py`). `prototype/app.html` is a static page generated from the pipeline by `build_app.py` + `prototype/app_template.html` (no server, opens with a double-click). Production: the same package behind FastAPI, run nightly (04_architecture.md).
