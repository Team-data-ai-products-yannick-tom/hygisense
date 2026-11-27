# 06_07 — Experiments & operations · Hygisense

> Baselines: `02_sizing.xlsx`, `05_metrics.md`, `evals/report_v0.md`. Names: Yannick = PM · Tom = engineer · Nissrine = Head of Operations.

## §1 Hypothesis and design

**The sentence we can be wrong about.**
> If we show BUY lines for ANSM declarations to the pharmacists of the pilot groupement, then the share of declarations that empty the pharmacy's shelf within 12 weeks moves from **69 %** (backtest do-nothing, large pharmacy: 31 of 45) to **59 % or less** by week 12, **without** the pharmacy's stock value rising more than 10 %, and **without** useless buy-aheads exceeding 60 % in any pharmacy-size segment.

The baseline is an outcome that exists with or without Hygisense, a shelf that empties. Our 63.5 % is a property of the system, not an outcome.

**Unit: one (pharmacy × ANSM declaration).** Each time a declaration hits a product the pharmacy sells, a coin decides whether the BUY line is shown (treatment) or hidden (control: the pharmacy does as today, with DP-Ruptures).

| Design | Why / why not for us |
|---|---|
| **A/B on (pharmacy × declaration)** ✅ | ~4 declarations per pharmacy per month (backtest: 45 in 10.5 months) gives enough units. Leak: a pharmacist who learns from the BUY lines may check ANSM by themself on control products. That pulls the effect **towards zero**, so a win is conservative. |
| A/B on pharmacies (clusters) | Cleanest, but 100 pharmacies = 50 per arm: only a huge effect would show. Used for the **holdout** after launch. |
| Shadow mode ✅ first | Weeks 1–2 of the pilot: lines computed, never shown; we check that the screen is ready by 7:30 and that the numbers match the backtest. |
| Before/after | Rejected: shortages are seasonal (winter), so any change in the period would land in the effect. |

**How the designs chain.** Shadow mode, 2 weeks → A/B on (pharmacy × declaration), enrolment until 722 units, then 12 weeks of reading → rollout by groupement → **5 % holdout of pharmacies** with no BUY lines for 6 months, to see if the effect lasts.

## §2 Sample size and the decision rule — written before the first declaration

| Step | Value | From |
|---|---|---|
| Today's rate | 69 % of declarations empty the shelf within 12 weeks | backtest do-nothing (`evals/backtest_events.csv`) |
| Smallest drop worth seeing | **−10 points** (69 % → 59 %): below that the product gate (21 % anticipated) is not met, so we would not roll out anyway | 02_sizing product gate × 69 % ≈ 14 pts, rounded down |
| Risks accepted | 5 % false win, 20 % missed win (standard) | convention |
| Units per group | **361** (two-proportion test) → **722** pharmacy-declarations | calculator; −5 pts would need 1,398 per group |
| Duration | 100 pilot pharmacies × ~4 declarations/month ≈ 400 units/month → **2 months of enrolment + 12 weeks of reading** (the read date of the outcome) | — |

**Decision rule (read once, at week 12 after the last enrolment):**
- **Ship** (roll out to the groupement) if the shelf-empty rate drops by **≥ 10 points**, stock value rises ≤ 10 %, useless buy-aheads ≤ 60 % in every segment, and 0 buys above the cap.
- **Iterate** if the drop is 4 to 10 points: fix one miss of spec v2, then run the same protocol again.
- **Kill** if the drop is < 4 points, or if any guardrail band is broken at a weekly read.
- **Stop early only on harm**, never on a good number: a network freeze triggered on more than 3 products in a week, or a wholesaler complaint about panic buying.

**Segments, pre-registered:** pharmacy size (small/large) · tension vs rupture · MITM vs not. Nothing else will be reported.

**The six questions, in words.** (1) The control is the same pharmacy on another declaration, so the season, the groupement and the pharmacist are the same. (2) We split pharmacy × declaration; the leak goes from treated lines to control products, and it shrinks the effect. (3) −10 points is the smallest drop that pays; smaller effects would need 4× the units. (4) The slowest read is the outcome itself (12 weeks); stock value reads at week 4. (5) Ship/iterate/kill is written above; harm stops it and Yannick + the groupement's pharmacist referent sign. (6) Plan B, if a groupement refuses randomisation: shadow mode on all, then compare with the same pharmacies' 2025 declarations.

## §3 Monitoring — four layers, four clocks, four owners

| Layer | What we watch | Threshold that pages someone | Clock | Owner | Tool (startup) |
|---|---|---|---|---|---|
| Infrastructure | nightly job done · screen ready by 7:30 · BDPM download · each pharmacy's export received | job failed · screen not ready at 7:30 · export missing for > 1 day | real time | Tom (on call) | Render logs + Sentry, Slack webhook |
| Model / system quality | anticipation on the backtest re-run with each new monthly BDPM file · forecast WAPE on a 5 % sample of products · AUC of the WATCH model | anticipation < 50 % on a re-run · WAPE > 35 % two weeks in a row | monthly / weekly | Tom | `run_eval.py` in CI, results in the repo |
| Product & guardrails | buys above the cap (must be 0) · **network buy volume per product** · freezes · useless buy-aheads by segment · lines ticked · **wholesaler service rate for pharmacies without Hygisense** (5 % holdout + one partner wholesaler) | any buy above the cap · network volume > 25 % of 2-week demand → freeze · useless > 60 % 2 months running · service rate outside our network down > 5 pts on a product → freeze | daily | Nissrine | one SQL table + Metabase |
| Business | boxes missing after declarations · stock value · time diary | stock value + 10 % · boxes missing not falling by month 3 | monthly | Yannick + pharmacy owner | monthly query, shared sheet |

**The first drift to hit us: the source itself.** The BDPM becomes "Info Médicament" in January 2027 (ANSM announcement): new file formats, new URLs. Signal: the BDPM download fails or the number of declarations read drops by more than 50 % from one month to the next. Response: no BUY lines (stale-data rule), fix the loader, re-run the backtest before switching back on. Next ones: **concept drift**, if wholesalers' stock obligations or MITM safety-stock rules change, the 2-week buffer changes (re-run the sensitivity table). **Data drift**: a pharmacy changes its software and the export changes.

**Where it runs.** FastAPI on Render (free tier for the pilot) · the static screen on the same service · traces in Grafana Cloud free tier via OpenTelemetry · no LLM key in the MVP · secrets in `.env`, never in Git.

## §4 Incidents and rollback

**One trace per pharmacy per night (OpenTelemetry spans):** `ingest_bdpm` (file date, rows) → `ingest_export` (pharmacy, rows, date) → `forecast` (products, WAPE sample) → `declared_flag` (declarations matched) → `risk_score` (model version) → `decide` (BUY/WATCH/TOO LATE counts, max qty / cap) → `render` (ready time) → `pharmacist_decision` (lines ticked, edited, refused). Attributes: rule version, model version, BDPM date. No patient field exists.

| Class | Example | How we see it | Action |
|---|---|---|---|
| Caught | a BUY line refused by the pharmacist; a FROZEN product | `pharmacist_decision` = refused · `decide` FROZEN | count it; weekly review; a spec line if it repeats |
| Wrong but harmless | useless buy-ahead (shelf would not have emptied) | useless share by segment | iterate the rule (spec v2 change 2) |
| **Harmful** | many pharmacies buy the same product on a declaration and drain a wholesaler; a non-substitutable product shown as a generic | network volume > 25 % · wholesaler or ANSM complaint · any report on generics | **rollback now** (below) · incident report · tell the groupement |
| Outage | BDPM unreachable · export missing | span errors · stale-data rule fires | automatic: no BUY lines, banner "data out of date" |

**Rollback plan**

| Field | Hygisense |
|---|---|
| 1 · Trigger | any buy above the cap · network freeze on > 3 products in a week · useless > 60 % two months running in a segment · a harmful incident |
| 2 · Who decides | **Nissrine (Head of Operations)**; at night **Tom** (on call), who then calls Nissrine |
| 3 · Action | switch → **SUGGEST-ONLY** (L1: lines visible, nothing can go into the draft) for the network or one segment; **OFF** = screen paused; redeploy the previous version if a release caused it |
| 4 · Time | under 15 minutes, one person, from a phone (feature flag) |
| 5 · What people see | pharmacists: "Recommendations paused — order as usual"; patients: nothing changes; traces keep logging |
| 6 · Last tested | 19 Nov 2026, on the prototype (`prototype/app.html`: ON → SUGGEST-ONLY → OFF, draft emptied). **Next test: in staging with Nissrine and Tom during the 2 weeks of shadow mode, then every quarter.** |

## §5 Who owns what

| Decision | Owner | Written where |
|---|---|---|
| Run the experiment on real pharmacies | Yannick (PM) proposes; **the groupement's pharmacist referent signs** | §1–§2 · governance.md |
| Read the weekly numbers and act | Yannick (PM), every Monday | §3 |
| Press the switch | **Nissrine**; Tom at night; each pharmacist for their own pharmacy | §4 · governance.md |
| Approve a release (rule, model, new BDPM format) | Yannick, with `run_eval.py` re-run and 20/20 cases attached | evals/README.md |
| Keep the traces, answer a pharmacy, a groupement or ANSM | Tom keeps the logs (12 months); Yannick answers | governance.md |
