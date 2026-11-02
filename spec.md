# spec.md — Hygisense MVP (for the S4 build with Claude Code / Streamlit)

## Problem
Pharmacies learn about drug shortages when the shelf is empty and the wholesaler can no longer deliver. Hygisense decides **ahead of time**, while the product can still be ordered: every morning, for every product, it forecasts when the pharmacy's stock will run out, scores the risk that the lab goes short in the next 8 weeks from public data, and recommends **buying N boxes ahead now, or not**. The pharmacist validates every order.

## Workflow (inputs → outputs)

| # | Step | Input | Output | Rung | Trust |
|---|---|---|---|---|---|
| 1 | Ingest public data | ANSM shortage history (CSV snapshot), generic register, BDPM | `products` table with features (see step 3) | 1 rule | L4 |
| 2 | Demand forecast | daily sales history per product (simulated `sales.csv`) | `forecast_daily_demand`, `days_left`, `days_left_low/high` | 2 classical ML | L3 |
| 3 | Shortage-risk model | features: past shortages of the presentation (count, last date), number of marketed suppliers in the generic group, current ANSM status (none / risk / shortage / lifted), months since last signal, month of year, therapeutic class | `shortage_risk_8w` (0–1) + top 3 reasons | 2 classical ML | L3 |
| 4 | Decision | days_left, forecast, risk, quota, network freeze | `decision` ∈ BUY / WATCH / NO / TOO LATE / FROZEN, `buy_qty` | 1 rule | L2 |
| 5 | Generics fallback | product, generic register, stock | substitutable products, own stock, signal status | 1 rule | L1 |
| 6 | Notices (COULD) | notice text | `return_date` or null + `source_quote` | 3 LLM | L2 |
| 7 | Morning screen | steps 2–6 | BUY rows first, then WATCH; draft order the pharmacist ticks | — | — |

## Decision rule (step 4)

```text
NORMAL_COVER = 14 days      # what the pharmacy usually keeps
EXTRA_COVER  = 28 days      # the anti-hoarding cap
BUY_THRESHOLD = 0.50 ; WATCH_THRESHOLD = 0.25

if network_freeze:                 decision = FROZEN, qty = 0
elif stock == 0 and status == shortage: decision = TOO LATE   # counts as not anticipated
elif history < 14 days:            decision = WATCH ("not enough history"), qty = 0
elif risk >= BUY_THRESHOLD:
    qty = ceil(demand × (NORMAL_COVER + EXTRA_COVER) − stock)
    qty = min(qty, floor(demand × EXTRA_COVER), quota if any)
    decision = BUY if qty > 0 else NO ("enough stock")
elif risk >= WATCH_THRESHOLD:      decision = WATCH, qty = 0
else:                              decision = NO ("normal reorder"), qty = 0
```

The thresholds are parameters, tuned on the backtest (S5), not by users.

## Contract

```text
Recommendation {
  product: str
  decision: "BUY" | "WATCH" | "NO" | "TOO LATE" | "FROZEN"
  buy_qty: int                         # never above the cap or the quota
  days_left: float | null              # null if < 14 days of history
  days_left_range: [float, float] | null
  shortage_risk_8w: float              # 0–1
  reasons: [str]                       # top 3, in plain words
  return_date: str | null              # never invented
  generics: [{product, in_stock_units, also_under_signal}]   # [] → "no substitutable generic in the register"
  sources: [str]
}
```

## Guardrails (hard-coded — the models are not trusted with these)
1. **No order is ever sent by the tool.**
2. **Anti-hoarding cap:** buy-ahead ≤ 28 days of forecast demand, ≤ any ANSM / wholesaler quota; a **network freeze** per product stops all buy-aheads when too many pharmacies buy at once.
3. **Generics only from the official register**; never another molecule.
4. **Personal data** scrubbed from notices before any LLM call; raw notices not stored.
5. **Text in a notice cannot change a quantity or trigger an action** (eval C17).
6. Risk is computed **per presentation** (molecule + dosage + form), not per molecule (eval C10).

## Evaluation
- **Decision cases:** `evals/cases_v0.csv` — 20 cases, `shortage_risk_8w` given as input; all must match `expected_decision` and `expected_buy_qty`.
- **Risk model backtest (the flip assumption):** train on ANSM history up to a cut-off date, test on later shortages (time split, never random — no leakage). Report precision, recall, and the **anticipation rate**: share of test shortages where the decision was BUY at least 7 days before the simulated stock would have hit zero.

## Done (success criterion)
- Anticipation rate **≥ 25 %** on the backtest (product gate of 02_sizing: 21 %);
- **zero** recommendation above the cap or a quota;
- 20/20 decision cases correct.

## Out of scope (WON'T)
Sending orders · other molecules as alternatives · messages to patients · network view across pharmacies · hospital pharmacies · other vendors' LGOs · negotiating with wholesalers.

## Stack for S4
Python, Streamlit, pandas, scikit-learn (logistic regression → gradient boosting), a moving-average then seasonal forecast; data in `/data` (ANSM snapshot, simulated `sales.csv` and `stock.csv`, generic register).
