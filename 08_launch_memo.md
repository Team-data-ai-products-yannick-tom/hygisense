# 08 — Launch memo · Hygisense

> To: Hygisense founders and the pilot groupement · From: Team TYN · 26 November 2026 · one page

**1 · The decision — YES, on one condition.** We launch a **pilot with one groupement (100 pharmacies)** from **1 February 2027**: 2 weeks in shadow mode, then the A/B test of 06_07 §1–§2. **Condition to go further: shelf-emptying declarations down by at least 10 points at week 12, with stock value up by 10 % at most.** We decide again on **30 June 2027**. Budget: the 02_sizing base case, **€192k a year**. The pilot itself is mostly integration (€60k: the stock export from the pharmacy software) and go-to-market (€30k). Supervision and evaluation (€35k) pay for the weekly review of the numbers and the rollback tests.

**2 · The proof.** On real 2026 data (ANSM, FDA, Sentinelles) and two simulated pharmacies, Hygisense said "buy now" in time for **63.5 % of the shortages that would have emptied the shelf** (33 of 52), against a criterion of 25 %, with 0 buys above the cap, **20/20** guardrail cases and 29 % useless buy-aheads. Boxes missing at the counter in the 12 weeks after a declaration fell by 48 % in the large pharmacy (56 → 29). **Before any alert**, the vigilance index (incl. *already short in the US*, ×2.1–2.4) puts 28 % of the next 8 weeks' declarations in its top 10 %; replayed in the large pharmacy, it flagged **15 of 43** 2026 declarations at least a week before the lab declared them (3× chance, often 8 weeks ahead): useful to watch and to buy a little ahead, not yet to drive the main purchase. The honest part: purchases are triggered by a rule on the ANSM declaration, while wholesalers must still deliver (2 weeks by law); all 19 misses are slow movers. The test must show the shelf-empty rate going from **69 % to 59 % or less**.

**3 · The steps.**
| Step | Who gets it | For how long | What must be true to go on |
|---|---|---|---|
| 1 Shadow | 100 pilot pharmacies, lines computed but not shown | 2 weeks | screen ready by 7:30 every day; numbers match the backtest; rollback tested |
| 2 A/B | same pharmacies, BUY line shown on half of the declarations | until 722 pharmacy-declarations, + 12 weeks | the decision rule of 06_07 §2 says ship |
| 3 Groupement | all pharmacies of the groupement (~1,500) | 6 months | network freeze triggered < 3 times a month; useless < 60 % |
| 4 Second groupement | ~3,000 reachable pharmacies, **5 % holdout** without BUY lines | ongoing | adoption ≥ 15 % by Q4 (the S2 flip) |

**4 · How to stop it.** We stop if a buy goes above the cap, if more than 3 products are frozen in a week, if useless buy-aheads exceed 60 % for two months in a segment, or after any harmful incident (a wholesaler drained, a wrong generic shown). **Nissrine (Head of Operations)** switches to **SUGGEST-ONLY** (lines shown, nothing can be ordered) or **OFF** in **under 15 minutes**, from a phone; Tom covers nights. Last tried: **19 November 2026 on the prototype**. Next try: in staging during the shadow weeks, then every quarter.

**5 · Who is responsible.**
| Decision | Name |
|---|---|
| The rule, the numbers every Monday, releases | **Yannick** (PM) |
| The switch, the network freeze, incidents | **Nissrine** (Head of Operations) |
| Data pipeline, traces, on call | **Tom** (engineer) |
| Each order | **the pharmacist** — Hygisense never sends one |
| **Signs the launch** | **Yannick and Nissrine for Hygisense, and the groupement's pharmacist referent for the pilot** |

**6 · What we do not know yet.**
1. **Do wholesalers really keep delivering for ~2 weeks after a declaration?** It is the legal minimum, and the whole result depends on it (0 days → 0 % anticipated). We need to check it with one wholesaler and the shadow-mode data.
2. **Do pharmacists tick the lines, and do they mind the useless ones?** We have not interviewed pharmacists, so this is the first thing the pilot measures (lines ticked, refused).
3. **What happens when many pharmacies buy on the same declaration?** The backtest simulates one pharmacy. The network cap (25 % of normal 2-week demand, split pro rata) is designed but not calibrated on real volumes; the A/B cannot see harm to pharmacies outside our network, so we read the wholesaler service rate of the 5 % holdout and of one partner wholesaler.

*With three more months:* archive the BDPM every month to build a real history, retrain the risk model on it, fix the three misses of spec v2, and build the network pieces of spec.md (pro-rata cap, local epidemic map from aggregated sales).
