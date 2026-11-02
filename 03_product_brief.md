# 03 — Product brief · Hygisense (v1)

> Team TYN · v1 written from 01 and 02 · **v2 after the user tests** (section 10). Users change the design, not the threshold.

## 1. Problem, user, do-nothing

**User:** the owner-pharmacist and the team who places orders (persona Claire, 01_problem_statement.md). **Problem:** the pharmacy learns about a shortage when the shelf is empty and the wholesaler can no longer deliver; ~10 h/week go into shortages. **Do-nothing:** DP-Ruptures, free, fires 72 h *after* the pharmacy failed to get a drug.

**Hygisense in one sentence:** *Every morning, for every product, Hygisense forecasts when the pharmacy's stock will run out and how likely the lab is to go short in the coming weeks, producing a recommendation — buy N boxes ahead now, or don't — that the pharmacist validates before any order is placed.*

The core idea: **decide while there is still stock and the product can still be ordered.** A product with 40 days of stock and a high shortage risk may need buying now; a product with 5 days and no risk only needs the normal reorder.

## 2. Process as-is → to-be (one product at risk, illustrative minutes — to measure in user research)

| Step | As-is (who, min) | To-be | Trust level | Metric per step |
|---|---|---|---|---|
| 1. Notice a product is at risk | Pharmacist, by chance (rep, colleague, ANSM site) or at the counter · 5 min | Shortage-risk score computed daily on all products · 0 min | L3 | Risk model precision / recall (backtest) |
| 2. Estimate how long the stock lasts | Mental estimate, often none · 5 min | Demand forecast → stock-out date with a range · 0 min | L3 | Forecast error (days) |
| 3. Decide whether to buy more, how much | Gut feeling, calls the wholesaler · **15 min** | Recommendation "buy N boxes / don't", capped, with its reasons · 2 min to validate | **L2** | Acceptance rate · useless buy-aheads |
| 4. When the shortage hits: find an alternative | Register, other wholesalers, colleagues · **20 min** | Rarer (stock bought ahead); generics from the register as fallback · 5 min | L1 | Stock-outs at the counter |
| 5. Patient at the counter | Explain, substitute or send away · 8 min | Rarer · 3 min | human | — |
| **Total** | **~50 min** | **~10 min when anticipated** | | |

The pain sits in steps 3 and 4. **The way back to a person:** the tool never orders; the pharmacist can refuse a recommendation, mute a product, or switch the tool off.

## 3. Features — RICE (reach = product-decisions per month in paying pharmacies; 375 pharmacies × ~50 products at risk, from 02_sizing)

| Feature | Reach / month | Impact | Confidence | Effort (person-weeks) | RICE | Decision |
|---|---|---|---|---|---|---|
| Demand forecast → stock-out date with a range | 18,750 | 2 | 80 % | 2 | 15,000 | **MUST** |
| Backtest eval-set (past ANSM shortages, time split) | 18,750 | 1 | 100 % | 1 | 18,750 | **MUST** |
| Buy-ahead decision rule, capped (anti-hoarding) | 18,750 | 3 | 80 % | 1 | 45,000 | **MUST** |
| Shortage-risk model from public data | 18,750 | 3 | 50 % | 3 | 9,375 | **MUST** |
| Generics from the official register (fallback) | 18,750 | 1 | 100 % | 1 | 18,750 | SHOULD |
| Draft order pre-filled with the recommended boxes | 18,750 | 1 | 80 % | 2 | 7,500 | SHOULD |
| LLM reading of lab notices (return date) | 5,300 | 1 | 50 % | 2 | 1,325 | COULD |
| Network view ("5 pharmacies nearby lack it") | 18,750 | 2 | 50 % | 5 | 3,750 | WON'T |

**The feature that tests the product gate is the shortage-risk model** (the flip assumption, adoption, is tested by a groupement pilot, not by a feature). Its RICE is the lowest of the MUSTs because our confidence is low — which is why we build it first, to learn.
**The cut that hurt most:** the network view. Pharmacists would love it, but it shares one pharmacy's stock with competitors.

## 4. MoSCoW — in scope / out of scope

| MUST (≤ 4) | SHOULD | COULD | WON'T (this time — dated 30/10/2026) |
|---|---|---|---|
| Demand forecast | Generics fallback | LLM reading of notices | Sending an order without the pharmacist |
| Shortage-risk model | Pre-filled draft order | E-mail / SMS alert | Suggesting another molecule |
| Buy-ahead rule, capped | | | Messages to patients |
| Backtest eval-set | | | Network view across pharmacies |
| | | | Hospital pharmacies · real-time integration inside pharmacy software (daily export only for now) |
| | | | Dynamic pricing / negotiating with wholesalers |

## 5. Data (from the audit — governance.md, S3)

Public: ANSM shortage history (labels for the risk model), generic register, BDPM (number of suppliers per molecule). Private: stock and sales **aggregated per product per day**, never per patient. **MVP: simulated stock and sales**, real ANSM history. Known gaps: ANSM lists mainly drugs of major therapeutic interest (other shortages under-labelled); demand forecasts noisier for small pharmacies.

## 6. Model — one rung per part

| Part | Rung | Why |
|---|---|---|
| Demand forecast → stock-out date | 2 · classical ML (moving average baseline → gradient boosting / seasonal model if it fails) | Demand varies with season and epidemics; must give a range |
| Shortage risk in the next 4–8 weeks | 2 · classical ML (logistic regression baseline → gradient boosting) | Tabular features: past shortages, number of suppliers, current ANSM status, season; explainable |
| Buy ahead or not, how many | 1 · rule | `buy if risk ≥ threshold and days_left < horizon`; quantity = demand until expected return, **capped at 4 weeks** and at any quota |
| Generics fallback | 1 · rule | The official register decides |
| Return date from notices (COULD) | 3 · LLM API + source quote | Free text |

## 7. Where it lives

A **morning screen** (web app) fed by a daily stock export from the pharmacy's own software; sold and rolled out through pharmacy groupements. Later: a badge inside the order screen of partner software vendors.

## 8. Success criterion (one sentence)

**"By Session 5, on a backtest of past shortages, Hygisense recommends buying ahead at least 7 days before the shelf would have been empty for at least 25 % of them — and never recommends more than the cap."**

| Metric | Threshold | Guardrail | Data | Date |
|---|---|---|---|---|
| Anticipation rate | **≥ 25 %** — the S2 product gate (21 %) with a margin | no buy-ahead above 4 weeks of normal demand · counter-metric: share of buy-aheads with no shortage after | ANSM history (time split) + simulated stock; evals/cases_v0.csv | Session 5 |

## 9. Risks and rollback trigger

| Risk | Signal | Rollback |
|---|---|---|
| Collective over-buying | Recommended buy-aheads on one product across many pharmacies exceed a share of national demand, or ANSM sets a quota | Freeze buy-ahead recommendations for that product network-wide the same day |
| Useless buy-aheads | > 50 % of buy-aheads followed by no shortage over a month | Raise the risk threshold |
| False reassurance | A stock-out on a product scored "low risk" | Review the case; DP-Ruptures stays the reference |
| Wrong generic shown | Any single case | Generics fallback switched off |

## 10. v2 — what the users changed (to fill after the tests, with evidence)

| Change | Evidence ("x of 5 users…") |
|---|---|
| *to fill* | *to fill* |

**What the users could not decide:** the 25 % threshold (S2 product gate), the models (backtest), the cap (governance).
