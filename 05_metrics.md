# 05 — Metrics · Hygisense

> Baselines from `02_sizing.xlsx` and `01_problem_statement.md`; component numbers from `evals/report_v0.md` (19 Nov 2026). Every arrow between two levels is a hypothesis that the A/B test (06_07) checks.

## §1 The evaluation stack — five levels, an owner and a clock each

| Level | What we measure on Hygisense | Today (v0) | When · how | Owner |
|---|---|---|---|---|
| **5 Business** | boxes missing at the counter after a declaration · pharmacist time on shortages · cash tied up in stock · (Hygisense: Q4 adoption ≥ 15 %, the S2 flip) | sizing baselines (§4) | after launch, monthly | Yannick (PM) + the pharmacy owner |
| **4 Product** | share of BUY lines ticked by the pharmacist · anticipation in production · useless buy-aheads | — | A/B, then weekly | Yannick (PM) |
| **3 Guardrails** | buys above the cap or a quota · network buy volume per product · stale data shown · personal data in the export | 0 above cap (backtest); 20/20 cases | before each release + daily in production | Nissrine (Head of Operations) |
| **2 AI system** | anticipation rate on the backtest · TOO LATE share · screen ready by 7:30 | **63.5 %** (criterion ≥ 25 %) | backtest at every change of rule, data or model | Tom (engineer) |
| **1 Model** | vigilance index AUC, share of declarations in its top 10 % · epidemic forecast error · demand WAPE | AUC 0.76 · 28 % (×2.8) · −9/−11 % vs baselines · WAPE 38 % / 52 % | offline, every commit | Tom |

Read bottom-up: a better AUC at level 1 is worth nothing if no BUY line comes from the index, which is the case today (it only feeds the WATCH list). Read top-down: the pharmacy owner's number (boxes missing, time) is the last to move and the only one they pay for.

## §2 When to stop — the stop criterion

> **We stop improving the vigilance index at AUC 0.76 because the decision does not use it:** every BUY comes from the ANSM declaration rule, and a better ranking of the WATCH list does not change what the pharmacy orders. A bigger model on the same snapshot overfits (gradient boosting: AUC 0.58). We reopen it when 12 monthly BDPM snapshots are archived, or when our pharmacies' supply failures are available (December 2027).

> **The next sprint goes to slow movers (all 19 misses)**, because the level above still responds there: each miss is a patient sent away. Useless buy-aheads (29 %) are within target and stay watched.

- **Floor, not a stop:** 0 buy above the cap or a quota; 20/20 decision cases. Any miss blocks the release.
- **Forecast:** the seasonal version did not beat the 56-day mean (42 % vs 38 % WAPE), so we stop at the mean (flat curve: the bottleneck is the declaration, not the forecast).

## §3 What we optimise, what we protect

| Kind | Metric | Level | Band / threshold |
|---|---|---|---|
| **Primary** | **Anticipation in production**: share of ANSM declarations hitting the pharmacy's products for which a BUY line was **ticked** while the wholesaler could still deliver | 4 | ≥ 25 % (product gate 21 %) |
| Guardrail 1 | Buy-aheads above the cap (28 days) or a quota | 3 | **0** — any breach = release blocked |
| Guardrail 2 | Network buy volume: boxes recommended on one product across all our pharmacies in one day, as a share of their normal 2-week demand | 3 | > 25 % → **network freeze** on that product |
| Guardrail 3 | Data freshness: BDPM file age · pharmacy export age | 2 | BDPM > 35 days or export > 1 day → no BUY line |
| Counter-metric 1 | **Useless buy-aheads**: shelf would not have emptied within 8 weeks anyway | 4–5 | target < 40 %; > 60 % two months in a row → harm threshold |
| Counter-metric 2 | **False reassurance**: stock-outs at the counter on products with no line on the screen (missed or undeclared) | 5 | tracked monthly; must not rise vs before Hygisense |

**Proxy vs outcome.** "Line ticked" (minutes) is easy to game: a screen that pushes BUY everywhere gets ticked more. So the primary is "ticked **and** the declaration would have emptied the shelf". The outcome, boxes missing at the counter, is read at week 12.

**By segment, always.** Report every metric by **pharmacy size** (small vs large), **declaration type** (tension vs rupture) and **MITM vs non-MITM**. In the backtest the small pharmacy anticipates less (57 % vs 68 %) and has a noisier forecast (WAPE 52 % vs 38 %). An average would hide both.

**The governance.md line (harm threshold):** "If useless buy-aheads exceed 60 % for two consecutive months in a segment, Hygisense drops to SUGGEST-ONLY (L1) on tensions for that segment until the cause is explained. Owner: Nissrine (Head of Operations). Reviewed monthly with the PM."

## §4 Three business metrics with expected effects

| Business metric | Baseline | Expected effect | It is a hypothesis about… | Lag | Read date |
|---|---|---|---|---|---|
| **Boxes missing at the counter** in the 12 weeks after an ANSM declaration on a product the pharmacy sells | backtest do-nothing: **1.2 boxes per declaration** (large pharmacy, 56 for 45 declarations in 2026); sizing: ~100 patients turned away / month (guess) | **−48 %** large (56 → 29), **−14 %** small (14 → 12) if the BUY lines are followed. Diluted to **≈ −20 %** on all patients turned away, if half of the shortages a pharmacy feels are declared to ANSM (guess) | pharmacists tick the lines (product) × declarations are early enough (wholesaler buffer ≥ 7 days) | 12 weeks | week 12 of the A/B |
| **Pharmacist time on shortages** | **10 h/week** (PGEU survey 2024-25, measured, self-reported) | **−2.9 h/week** → ~7 h (sizing branch A: 60 % time saved when known a week ahead, on the anticipated share) | the time goes to searching after the fact, not to reading the screen | 4 weeks | week 4 of the A/B (time diary, 1 week before / 1 week after) |
| **Cash tied up in stock** (inventory value, days of stock) | pharmacy's own figure at the start (≈ 30 days of stock, analogy — to measure) | **unchanged, ±5 %**, stated as a non-effect. **Stop band: > +10 %** | the cap (28 days) and the useless share keep extra stock small | 4 weeks | week 4, then monthly |

How they trace: boxes missing ← anticipation × lines ticked × buffer (components 3a, 4). Time ← anticipation (component 3a). Cash ← useless buy-aheads × cap (component 4). For Hygisense itself, the flip metric stays **adoption ≥ 15 % of reachable pharmacies by Q4** (02_sizing), read on the groupement pilot.

## §5 The evaluation plan

| Set | Size today | Target | Labels | Re-run when |
|---|---|---|---|---|
| Decision cases (`evals/cases_v0.csv`) | 20 | 40 (add the 3 v2 changes + the "already short" case) | written before the build, checked by a second person | every change of the rule |
| Backtest events | 44 shortages that empty a shelf (2 pharmacies, 2026) | **100+**: 4 more simulated pharmacies (sizes, regions) + 2025 once archived | ANSM declarations (BDPM) — nobody labels by hand | every change of rule, data or model; every new monthly BDPM file |
| Risk model rows | 117,476 product-dates, 326 declarations (test) | + every new monthly snapshot | ANSM | monthly |
| Adversarial set (optional) | C09 (patient name), C17 (prompt injection), C20 (freeze) | + a fake BDPM line, a negative stock in the export | by hand | each release |

**No LLM judge**: there is no generated text in the MVP. If the COULD feature (lab notices) is built, we write the rubric first, grade 30 notices in pairs, and validate the judge against us before using it.
