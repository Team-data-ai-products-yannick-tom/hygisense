# 02 — Investment memo · Hygisense

> To: Hygisense founders and investors · From: Team TYN (Tom, Yannick, Nissrine) · Base case = 02_sizing.xlsx

**Recommendation: CONDITIONAL GO — build the MVP, and launch only if (1) a groupement pilot shows that at least 15 % of reachable pharmacies would subscribe within a year, and (2) the backtest shows Hygisense says "buy ahead" in time for at least 25 % of past shortages. Otherwise the team builds the tiers-payant rejections tool instead. We orchestrate: two classical ML models and capped rules on public data, plus an LLM API for free-text notices.**

## 1. How much?

**For one pharmacy (the customer's business case)**

| Branch | Base case | Type |
|---|---|---|
| A. Time saved | €5.4k / year (≈ 2.9 h/week × €40 × 47 weeks) | survey + guess |
| B. Sales protected (100 patients/month turned away today × €15 × 25 % margin × 50 % anticipated) | €2.3k / year | guess → interviews |
| C. Chronic patients kept (5/month who would leave × €300 margin/year × 50 % anticipated) | **€9.0k / year** | guess → interviews |
| **Value per pharmacy** | **€16.6k / year** for a €99/month subscription (€1,188) → **ROI 14×** | derived |

Not counted: patients won from neighbouring pharmacies in shortage. It disappears when every pharmacy uses the tool.

**For Hygisense (year 1, base case)**

| | Value | Type |
|---|---|---|
| Reachable pharmacies (2 groupement partnerships) | 3,000 | case assumption |
| Adoption | 5 → 20 % by Q4 (375 paying on average) | **guess → pilot** |
| Revenue | **€446k** · €713k run-rate at end of year | derived |
| **Net value** | **€254k** | derived |

Market: 19,627 pharmacies in France → TAM €23M/year at our price (€326M of value created). SAM = reachable pharmacies, €3.6M/year.

## 2. How sure?

| Scenario | p | Net value, year 1 |
|---|---|---|
| Pessimistic | 0.25 | **−€174k** |
| Base | 0.50 | €254k |
| Optimistic | 0.25 | €1,003k |
| **Expected value** | | **€334k** |

**The assumption that flips the decision: adoption.** At **15 %** of reachable pharmacies by Q4 (instead of 20 %), the base case falls to the hurdle (sheet, Costs & Decision!D29). The pharmacist's ROI is so high that the risk is not "is it worth it for them?" but "will they hear of it and buy?". **How we test it:** a pilot with one groupement, or letters of intent, before scaling.

**The product gate (S4):** below **21 %** anticipation, the pharmacist's ROI falls under 6× and adoption collapses (Costs & Decision!D31). Our success criterion takes a margin: **≥ 25 %** on the backtest.

The pessimistic case combines everything going wrong: few patients turned away, low price, half the adoption.

## 3. What if we're wrong?

- **Cost lines, base: €192k/year.** Integration & models €60k, go-to-market €30k (a start-up has to sell), supervision €20k, evaluation €15k, monitoring €12k, re-evaluation €5k, tokens **€2k**, cost of error €48k (churn €45k + tail €3k). Tokens ×10 still leaves €233k: **not a cost arbitrage.**
- **The tail:** two errors are **legal and health risks**, not only money: showing a product as substitutable when it is not, and **collective over-buying** (thousands of pharmacies buying ahead at once and draining a wholesaler — the tool would create the shortage it predicts). Priced at 2 % × €150k a year; blocked by rules: official generic register, buy-ahead capped at 4 weeks of normal demand and at any ANSM quota. **Owner: the product owner** (governance.md).
- **The silent cost:** useless buy-aheads tie up the pharmacy's cash; too many and pharmacists stop following the advice — modelled as 10 % churn. Counter-metric for S5: share of buy-aheads with no shortage afterwards.

## 4. Compared to what?

- **Do-nothing is not zero for pharmacies:** they have **DP-Ruptures** (Ordre des pharmaciens, free, built into their software), but it fires **72 h after** the pharmacy fails to get a drug. For Hygisense, do-nothing = no product, €0.
- **The hurdle:** the same team could build a **tiers-payant rejections tool** for pharmacies, estimated at **€150k net/year**. EV €334k and base €254k clear it; the pessimistic case does not → conditional go.
- **Strategic risk:** a pharmacy-software vendor, or the Ordre, adding "days of stock left + shortage risk" to DP-Ruptures. Our edge: the risk model and speed. We should prove it with a groupement fast.

## Build, buy or orchestrate?

| Question (course) | Build own model | Buy | Orchestrate |
|---|---|---|---|
| Our edge? (risk model on public data, decision logic) | 4 | 1 | 5 |
| A product does 80 % of the job? | — | 1 (none; DP-Ruptures is reactive) | — |
| Live in weeks? | 1 | — | 4 |
| 3-year cost | 2 | — | 4 |
| Data stays with us (no patient data anyway) | 5 | 2 | 4 |
| Can we leave? | 5 | 1 | 4 |
| People to run it | 2 | 4 | 3 |

**We orchestrate because** the two models are standard classical ML we train ourselves on public data (cheap, no GPU), the decision is a rule, and the LLM is only needed to read free-text notices — any API will do. **What would change it:** a vendor (or the Ordre) shipping the same view for free.
