# 03 — AI Lean Canvas · Hygisense

| Block | Content | Session |
|---|---|---|
| **Problem** | Pharmacists lose ~10 h/week on shortages and learn about them at the counter; DP-Ruptures only fires 72 h after the failed order | S1 |
| **Users** | Owner-pharmacists and their teams — 19,600 pharmacies in France, ~3,000 reachable through 2 groupement partnerships | S1 |
| **Value proposition** | Every morning: which products to **buy ahead now, and how many boxes**, because the lab is likely to go short before my stock runs out — and which ones not to bother with | S1 |
| **Solution** | Demand forecast (stock-out date) · shortage-risk score from public data · buy-ahead decision, capped · backtest eval-set | S3 |
| **Key metric** | Anticipation rate ≥ 25 % (product gate) · Q4 adoption ≥ 15 % (flip) (shortages for which it said "buy ahead" ≥ 7 days before the shelf would be empty) · guardrail: no buy-ahead above the cap | S3 |
| **Channel** | Sold through pharmacy groupements; a morning screen plugged into the pharmacy's own software via a daily stock export | S3 |
| **Unfair advantage** | A shortage-risk model trained on years of public ANSM history + the groupement channel; weak moat — speed matters | S2 |
| **Costs** | Base €192k/year: integration & models €60k, go-to-market €30k, supervision €20k, evaluation €15k, monitoring €12k, re-evaluation €5k, tokens €2k, cost of error €48k | S2 |
| **Value / revenue** | €99/month for €16.6k of value per pharmacy (ROI 14×) · base net €254k year 1 · EV €334k vs €150k hurdle (tiers-payant tool) → conditional go | S2 |

## The five AI blocks

| Block | Content |
|---|---|
| **Data** | ANSM shortage list, generic register, BDPM (public) · stock and sales per product per day (contract, no personal data) · MVP on simulated stock · gap: small pharmacies |
| **Model** | Classical ML ×2 (demand forecast, shortage-risk classifier) + capped decision rule + LLM API (free-text notices) — one rung per part |
| **Evaluation** | Decision cases: 20 now (evals/cases_v0.csv) · backtest of the risk model on past ANSM shortages (time split) for S5 |
| **Human in the loop** | L2 on every buy-ahead (pharmacist validates), L1 on generics; ordering stays with the pharmacist |
| **Risks** | Collective over-buying (bullwhip) · useless buy-aheads (cash) · wrong generic · false reassurance · DP-Ruptures adding the same view for free |
