# How the ML works — in plain words

Hygisense has **three** models. None of them decides a quantity: a rule does (step 4), and the pharmacist validates every line (step 5).

| # | Model | Question it answers | File | How good (2026 test) |
|---|---|---|---|---|
| 1 | Demand forecast | How many boxes will this pharmacy sell per day? | `hygisense/forecast.py` | WAPE 38.3 % vs 41.7 % for "same as last month" |
| 2 | Vigilance index | How likely is a shortage declaration on this drug in the next 8 weeks? | `hygisense/vigilance.py` | AUC 0.76; top 10 % of products hold 28 % of declarations; 15 of 43 declarations seen ≥ 1 week ahead in the demo pharmacy (3× chance) |
| 3 | Epidemic forecast | How many flu / respiratory cases in 4 weeks, in this region? | `hygisense/signals.py` (`EpidemicModel`) | 4-week error, Île-de-France respiratory: 50 vs 61 for "same as this week" |

## 1 · Demand forecast (`forecast.py`)
Average daily sales of the last 56 days, with its spread. We tried a seasonal version: it was worse, so we kept the simple one.

## 2 · Vigilance index (`vigilance.py`) — the "before the alert" model
We tried a logistic regression and gradient boosting first: AUC 0.58–0.68, unstable. We replaced them with a score a pharmacist can check by hand.

1. Five yes/no **flags** per drug: major therapeutic interest (ANSM list) · only one lab in France · already short in the US (FDA) · nervous-system drug · same molecule already short in France.
2. For each flag, on 2025 data: *declaration rate with the flag ÷ rate without it* = **relative risk**.
   Measured: major interest ×8.1 · same molecule short ×7.0 · one lab ×4.4 · US shortage ×2.5 · nervous system ×1.75.
3. **Index** of a drug = product of the relative risks of its flags (normalised so 1 = average drug).
4. **Probability in 8 weeks** = index × average declaration rate, capped at 90 %.
5. **Reasons** shown in the app = the flags, strongest first.

Example: MICROPAKINE L.P. 250 mg carries 5 flags → index ×77 → probability 7.8 % in 8 weeks (the average drug: 0.1 %).

## 3 · Epidemic forecast (`signals.py`)
For each week: `log(cases in 4 weeks) = a + b·log(cases now) + c·(2-week trend) + d·log(usual level for that week)`, fitted by least squares on weeks before 2024, then tested on 2023–2026. One model per region (Sentinelles, 22 regions).
In the app, if the region's forecast rises, the normal reorder of respiratory / anti-infective / pain drugs goes up by the same ratio, **capped at +40 %**.

## 4 · The rule (`decide.py`) — not ML on purpose
- Buy ahead only when a lab has **declared** a shortage and the wholesaler can still deliver (they must keep 2 weeks of stock, art. R5124-59 CSP).
- Quantity = up to **28 days** of forecast sales, never above an ANSM or wholesaler quota.
- **Network freeze** if too many pharmacies buy the same drug.
- Free text (an ANSM notice) can be shown, never change a quantity.

Re-run everything: `python run_eval.py` → `evals/report_numbers.json` and `prototype/app.html`.
