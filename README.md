# Hygisense — drug-shortage copilot for community pharmacies

Team **TYN** — Tom, Yannick, Nissrine · Albert School · Data & AI Product (MSA-DAT07-04), 2026–27

**In one sentence:** every morning, Hygisense checks the ANSM shortage declarations against the pharmacy's own stock and sales and recommends **buying N boxes ahead now — while the wholesaler can still deliver — or not**. The pharmacist validates every line; Hygisense never sends an order.

**Decision:** conditional go → **pilot with one groupement from 1 Feb 2027** (08_launch_memo.md).
**Evaluation v0** (real ANSM, FDA and Sentinelles data, 2026; simulated pharmacies): **63.5 %** of shelf-emptying shortages anticipated at the ANSM alert vs a 25 % criterion; **28 %** of the next 8 weeks' declarations seen coming *before* any alert by the vigilance index (top 10 % of products); 0 buys above the cap; 20/20 guardrail cases; epidemic forecast 9–11 % better than the baselines (evals/report_v0.md).

## Run it

```bash
pip install -r requirements.txt
python run_eval.py              # ~1 min: decision cases, risk model, backtest, rebuilds the demo
```
Then open `prototype/app.html` (double-click): the pharmacist's app — order (read-only, then edit), vigilance, reports, settings, method.

## Deliverables

| Session | File |
|---|---|
| S1 Diagnosis | `01_problem_statement.md` · `governance.md` |
| S2 Sizing | `02_sizing.xlsx` · `02_investment_memo.md` |
| S3 MVP design | `03_product_brief.md` (final v2) · `03_ai_lean_canvas.md` · `03_user_research.md` · `03_prototype_link.md` · `spec.md` (v2) |
| S4 Build & decode | `hygisense/` · `run_eval.py` · `prototype/app.html` · `evals/report_v0.md` · `04_architecture.md` |
| S5 Metrics | `05_metrics.md` · `evals/README.md` |
| S6–S7 Experiments & operations | `06_07_experiments_operations.md` |
| S8 Launch | `08_launch_memo.md` · tag `v1.0` |

**Data:** the official *Base de données publique des médicaments* (ANSM, HAS, UNCAM — files of 19 Nov 2026, Licence Ouverte), openFDA drug shortages, Réseau Sentinelles; see `data/README.md`. The pharmacy's stock and sales are **simulated**. No patient data is ever processed (`governance.md`).
**Company:** Hygisense is a fictional start-up that sells the product of the same name to pharmacies (€99/month).

**How the ML works, in plain words:** [`HOW_THE_ML_WORKS.md`](HOW_THE_ML_WORKS.md).
