# Evaluation report v0 · Hygisense

> Run: `python run_eval.py` · numbers in `evals/report_numbers.json` · events in `evals/backtest_events.csv`
> **Real data:** drugs and ANSM supply declarations (BDPM files of 19 Nov 2026), US drug shortages (openFDA, 1,556 records), French epidemics (Réseau Sentinelles, weekly since 2005).
> **Simulated:** the pharmacy, meaning its assortment (3,000 or 1,800 real references), its sales (≈ 6,500 € / 2,600 € a day of medicines) and its stock.
> **Time split:** fitted on 2024–2025, scored once on 2026. Nothing is tuned on 2026.

## The number against the criterion

**Criterion (03_product_brief.md):** on a backtest of past shortages, Hygisense recommends buying ahead at least 7 days before the shelf would have been empty for **≥ 25 %** of them, and never above the cap.

| | Result | Target | Pass? |
|---|---|---|---|
| **Anticipation rate** (test 2026, two pharmacies) | **63.5 %** (33 of 52 shortages that would have emptied a shelf) | ≥ 25 % (product gate 21 %) | ✅ |
| Buy-aheads above the cap or a quota | **0** | 0 | ✅ |
| Decision cases (`evals/cases_v0.csv`) | **20 / 20** | 20 / 20 | ✅ |
| Counter-metric: useless buy-aheads | **29 %** (12 of 42) | < 40 % | ✅ |
| **Shortages seen coming before any alert** (vigilance index, top 10 % of products) | **28 %** of the declarations of the next 8 weeks, ×2.8 vs random | — (new in v2) | — |

**Two layers, two kinds of anticipation:**
1. **At the alert (decides the purchase).** The morning the ANSM publishes a *tension* or *rupture* on a product the pharmacy sells, Hygisense says "buy N boxes now". It works because wholesalers must hold at least **two weeks** of their customers' consumption (art. R5124-59 CSP; 18.5 days on average, IGAS 2014): the product can still be ordered. DP-Ruptures only fires 72 h *after* the pharmacy's own order has failed.
2. **Before the alert (decides what to watch).** A vigilance index ranks every product by its risk of a declaration in the next 8 weeks: major therapeutic interest, a single lab, same molecule already short elsewhere, **already short in the United States**. The 10 % riskiest products hold 28 % of the declarations to come. That is useful for watching and preparing, but not precise enough to spend a pharmacy's cash on.

## Results by pharmacy (test window 1 Jan – 19 Nov 2026)

| | Large pharmacy | Small pharmacy |
|---|---|---|
| References stocked (real catalogue) | 3,000 | 1,800 |
| ANSM declarations on its products | 45 | 35 |
| … that would have emptied its shelf (do-nothing) | 31 (69 %) | 21 (60 %) |
| **Anticipated** (BUY ≥ 7 days before empty, still orderable) | **21 (68 %)** | **12 (57 %)** |
| on tensions / on ruptures | 65 % / 80 % | 50 % / 100 % |
| Boxes missing at the counter in the 12 weeks after each declaration: do-nothing → advice followed | 56 → 29 (**−48 %**) | 14 → 12 (**−14 %**) |
| Buy-ahead episodes / useless (shelf would not have emptied within 8 weeks) | 27 / 7 (26 %) | 15 / 5 (33 %) |
| Demand forecast error (WAPE, 14 days): 56-day mean → seasonal version | 38 % → 42 % | 52 % → 56 % |

## The key assumption: how long wholesalers keep delivering

| Wholesaler buffer after a declaration | Anticipation (large pharmacy) |
|---|---|
| 0 days | **0 %** |
| 7 days | 65 % |
| 14 days (legal minimum) | 68 % |

The rule depends entirely on this buffer, so **it is the number to check first** with one wholesaler and the shadow-mode data (08_launch_memo.md, part 6).

## Predicting before the alert: what we tried, what holds

Unit: product × date (117,476 product-dates in 2026, 326 declarations within the next 8 weeks).

| Model | AUC 2026 | Top 1 % riskiest: lift | Verdict |
|---|---|---|---|
| "Is it a drug of major therapeutic interest?" alone | 0.65 | — | the baseline to beat |
| v1 · logistic regression, 24 catalogue + history features | 0.68 | ×0 (no declaration caught) | unstable, kept only as a comparison |
| Gradient boosting, same features + FDA + epidemics (tested, not kept) | 0.57–0.58 | ×4–5 | overfits the short history |
| **v2 · vigilance index** (relative risks measured on 2025 only) | **0.76** (0.82 on 2025) | **×4.3**; top 10 %: ×2.8, 28 % of declarations | **kept** |

Relative risks of the index, measured on 2025: drug of major therapeutic interest **×8.1** · same molecule already short at another lab **×7.0** · single lab in France **×4.4** · **already short in the United States ×2.5** · nervous-system class ×1.8.

**The US signal is real and stable:** a product whose substance is short in the US is **×2.4** more likely to be declared short in France within 8 weeks in 2025, and **×2.1** in 2026. Once MITM status is known it adds little to the ranking, because most US shortages concern MITM drugs. 17 % of French products match a substance of the FDA list.

**Why not a "big model":** the history is the limit, not the algorithm. The BDPM file is a snapshot (declarations still listed in November 2026), and the FDA list keeps mostly current shortages. A bigger model learns unstable signs on such a short, biased history (the gradient boosting row above). The next real gain needs new data: monthly archives of the BDPM file, and the supply failures seen across Hygisense's own pharmacies.

## Epidemics: a forecast that works, used for quantities

Réseau Sentinelles, weekly incidence per 100,000. Forecast 4 weeks ahead, fitted before 2024, evaluated on mid-2023 → Nov 2026:

| Mean absolute error | Influenza-like illness | Acute respiratory infections |
|---|---|---|
| Persistence (this week's value) | 56 | 79 |
| Climatology (same week, past years) | 59 | 69 |
| **Hygisense model** (level + trend + climatology) | **50** (−11 %) | **63** (−9 %) |

Epidemics do **not** predict lab declarations (no positive effect in the index). They are used where they belong: the normal reorder of respiratory, anti-infective and analgesic products is raised by the forecast increase (capped at +40 %). That effect is **not yet measured**: our sales are simulated, so they cannot show it honestly.

## The three things to fix (→ spec.md v2)

1. **Slow movers: all 19 misses.** Every missed shortage is a product selling ≤ 2 boxes a month. The 56-day forecast is close to 0, so the rule buys nothing, and the shelf still empties weeks later. → *Spec v2: on a declaration, keep at least 2 boxes of any product sold in the last 6 months.*
2. **Useless buy-aheads (26–33 %).** Within target, but each one ties up cash. → *On a tension, buy only if the shelf empties within 8 weeks at 40 % delivery.*
3. **Old tensions still running** (108 products on the demo morning). Nothing can be anticipated any more for them. → shown apart as "déjà en rupture", left to DP-Ruptures and generics.

## What this evaluation does not prove (say it at the oral)

- **Snapshots, not full histories** (BDPM availability file, FDA list). Old short episodes are missing; 114 "back in stock" lines have no start date and are left out.
- **The pharmacy is simulated:** assortment, demand (long tail, generics sell more, expensive drugs sell less), reorder rule (order up to 14 days below 7 days). Real sales are lumpier.
- **One pharmacy at a time.** If every pharmacy bought on the same declaration, wholesalers would empty faster than simulated. The network freeze and the quotas in `governance.md` exist for that.
- **Tensions are modelled as "the wholesaler delivers 40 %"** after the buffer, and ruptures as 0 %. That is an analogy, not a measurement.
- **FDA ↔ France matching is by substance name** (first 6 letters of the normalized name, salts removed). It can merge or miss substances.

## Preuve d'anticipation avant l'annonce (pharmacie « grande », 2026)

Rejeu sans connaître l'avenir : chaque jour, l'indice de vigilance est calculé ; un produit est « repéré » s'il est dans le top 10 % de risque de la pharmacie entre 56 et 7 jours avant la déclaration ANSM.

| | Valeur |
|---|---|
| Déclarations 2026 sur les produits de la pharmacie | 43 |
| Repérées ≥ 7 jours avant la déclaration | **15 (35 %)** |
| Part des produits surveillés en moyenne | 11,2 % |
| Attendu au hasard avec la même surveillance | 4,8 |
| Gain sur le hasard | **×3,1** |

Exemples : ROPINIROLE EG 2 mg (repéré 18/03, tension 13/05), LARGACTIL 100 mg (09/04 → 04/06), BICAFRES 1000 mg (27/04 → rupture 22/06), KALEORID LP (26/06 → rupture 21/08). Non repérés : 28, dont FUROSEMIDE EG, NITRENDIPINE, TOUJEO.

Limite : l'indice est surtout structurel (MITM, source unique, pénurie US), il donne un risque et non une date. Dans l'app il alimente la section « Prévu par Hygisense — pas encore déclaré » (achat préventif proposé, jamais ajouté automatiquement) ; l'achat principal reste déclenché par la déclaration ANSM.
