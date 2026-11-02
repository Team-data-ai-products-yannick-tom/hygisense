# 01 — Problem statement · Drug-shortage copilot for community pharmacies

> Team TYN — Tom, Yannick, Nissrine · Data & AI Product (MSA-DAT07-04)
> Status: v1 (updated for S2–S3) — every number is tagged **measured / analogy / guess**. Guesses are hypotheses to test, not facts.

**The company (bring-your-own checklist).** **Hygisense** is a *fictional* French B2B SaaS start-up. Its product, also called Hygisense, is a shortage copilot that plugs into the pharmacy's existing software (LGO) through a daily stock export, sold as a monthly subscription (€99/month, base case). Market: the ~19,600 community pharmacies in France; go-to-market through pharmacy groupements (2 partnerships = ~3,000 reachable pharmacies, case assumption). **The decision:** the founders must choose what the team builds in the next six months: this copilot, or the next-best product (a tool that handles third-party payment rejections for pharmacies).

---

## 1. Problem statement

**Community pharmacists in France** lose **more than 10 hours a week** managing drug shortages — and, worse, patients: every missing drug sends a patient away, and a chronic patient sent away may never come back. **Today** they check the ANSM website and wholesaler portals by hand, phone wholesalers and colleagues, and discover most shortages at the counter, when the patient is already waiting. **Success looks like** a pharmacy that **buys ahead, in time,** for at least a quarter of the shortages that would have emptied its shelf — while there is still stock and the wholesaler can still deliver — keeping its patients and about **€16k a year** of value (02_sizing.xlsx), without overstocking.

**Key figures**

| Figure | Value | Source | Type |
|---|---|---|---|
| Shortage and shortage-risk reports handled by ANSM in 2025 | 3,887 (3,488 risks + 399 actual shortages) | ANSM, Rapport d'activité 2025 (annexes) | measured |
| Same figure in 2024 | 3,825 | ANSM, Rapport d'activité 2024 | measured |
| Time spent by European community pharmacies limiting shortages | > 10 h/week, +4 h vs 2022 | PGEU survey (Nov 2024 – Jan 2025) | measured (survey, self-reported) |
| Time spent in 2021 | 5.3 h/week | PGEU survey, via Ordre des pharmaciens | measured (survey) |
| Community pharmacies in metropolitan France (2024) | 19,627 (−1.3 % vs 2023) | Ordre des pharmaciens, Panorama 2024 | measured |
| Pharmacies connected to DP-Ruptures in integrated mode | 14,575 | Ordre des pharmaciens | measured |
| Loaded cost of one pharmacist hour | €40–50 | guess — to replace with a real salary grid | guess |

---

## 2. Problem tree

| Level | Content |
|---|---|
| **Symptom** | "I spend my week chasing drugs instead of advising patients." |
| **Problem** | The pharmacist learns about a shortage too late — when the patient is at the counter or the order comes back empty. |
| **Cause** | Information is scattered (ANSM list, wholesaler portals, lab notices) and **not cross-checked with the pharmacy's own stock and consumption**. Nobody tells the pharmacist "*this* shortage will hit *you* in 6 days". |
| **Testable solution** | Every day and for every product: (1) an ML forecast of **demand** gives the date the pharmacy's own stock will run out; (2) an ML **shortage-risk score** built on public data (ANSM signals and their history, number of generic suppliers, past shortages of the molecule, season) estimates the probability that the lab stops supplying in the coming weeks; (3) a decision rule combines both: **buy ahead now (how many boxes) or not**. Generics from the official register are shown as a fallback. |

### 5-Whys

1. Why do pharmacists lose 10 h/week? — They look for alternatives drug by drug, often in a hurry.
2. Why in a hurry? — They discover the shortage when the shelf is empty.
3. Why so late? — Shortage notices are public, but nobody checks them against the pharmacy's stock every day.
4. Why not? — It is manual: several sources, hundreds of references, no time.
5. Why manual? — The pharmacy software (LGO) handles orders, not external shortage signals. → **This is the why we act on.**

---

## 3. Jobs-to-be-Done

> "When a drug I dispense regularly is likely to go short at the lab, I want to know **today, while I still have stock and can still order it**, whether to buy more and how much — so that no patient leaves without their treatment, **without** tying up cash in boxes I will not sell."

---

## 4. Press release (dated 12 months from today)

> **Paris, October 2027** — *[Product name]* today announced that pharmacies using its shortage copilot now **buy ahead in time for one shortage in two** that would have emptied their shelves, and have cut the time spent on shortage management by **about 3 hours a week**. "I used to find out at the counter. Now every morning it tells me: buy 30 more boxes of this one now, don't bother with that one," said a pharmacist in Asnières. The copilot reads public ANSM data and the pharmacy's own stock — **no patient data ever leaves the pharmacy**.

### What would have to be true

1. Public data (ANSM signals and their history, supplier structure, seasonality) carry enough signal to **predict a lab shortage weeks ahead** — better than waiting for the ANSM announcement — otherwise there is nothing to anticipate.
2. The pharmacy's stock and sales history can be **exported or read** from its software (LGO) at least daily.
3. Pharmacists **act on a morning alert** (reorder, switch wholesaler, prepare a substitute) rather than ignoring it — alert fatigue is the main risk.

---

## 5. Persona & journey map

### Persona — Claire, 38, owner-pharmacist, Île-de-France

| | |
|---|---|
| **Goal** | Serve every patient their treatment; keep stock lean (cash is tied up in it) |
| **Pain** | 10 h/week on shortages; arguing with patients over missing drugs |
| **Tools** | Her LGO (pharmacy software), wholesaler portals, ANSM website, phone |
| **Fear** | A chronic patient (e.g. on an antiepileptic) leaving without treatment; a tool that floods her with useless alerts |

### Claire's journey today — where the pain sits

| Step | Today | Pain |
|---|---|---|
| 1. Order arrives with missing lines | Notices the drug is "manquant" | medium |
| 2. **Find out why and for how long** | Checks ANSM, wholesaler portal, calls the rep | **high** |
| 3. **Find an alternative** | Looks for a generic or another wholesaler | **high** |
| 4. Patient at the counter | Explains, substitutes or sends them elsewhere | high (emotional) |
| 5. Reorder | Places orders with several wholesalers | medium |

The copilot lands on steps 2 and 3 — and moves them **before** step 1.

### The second journey — the patient

Arrives with a prescription → drug missing → waits, comes back, or goes to another pharmacy → loses trust. The product never talks to the patient directly; it reduces how often this happens.

---

## 6. Stakeholder map

| | **Low interest** | **High interest** |
|---|---|---|
| **High power** | **Keep satisfied** — LGO software vendors (integration), Ordre des pharmaciens | **Manage closely** — owner-pharmacists (buyer and user), pharmacy groupements (could buy for their network) |
| **Low power** | **Monitor** — patients, ANSM (data source) | **Keep informed** — pharmacy staff (préparateurs), wholesalers |

---

## 7. Is AI the right tool?

| Task | Level | Why |
|---|---|---|
| Fetch ANSM signals, generic register, public drug database every day | **Rule / automation** | Scheduled ingestion — no AI needed |
| Forecast **demand** per product → date the pharmacy's stock runs out | **ML (time series)** | Consumption varies with season and epidemics (amoxicillin in winter) |
| Predict the **risk of a lab shortage** in the next 4–8 weeks per product | **ML (classification)** | Learned on ANSM history: past shortages of the molecule, number of suppliers, current "risk" signals, season |
| Decide **buy ahead or not, and how many boxes** | **Rule on top of the two models** | Buy if P(shortage) × days of stock left calls for it; quantity capped (anti-hoarding guardrail) — explainable |
| List substitutable generics as a fallback | **Rule** | Official generic register — a lookup |
| Read free-text lab notices ("retour prévu S48") | **GenAI (LLM)** | Free text, heterogeneous formats |

**Honest answer to question 1 of the course ("is there a rule that solves 80 %?"): no for the anticipation itself — a fixed rule cannot say when *this* pharmacy runs out nor which molecule will go short next; yes for everything around it.** Two classical ML models do the anticipation, rules make the decision explainable, and the LLM only reads free text.

### Rapid feasibility check

| Question | Colour | Note |
|---|---|---|
| Usable data? | 🟡 Yellow | ANSM data public; pharmacy stock must be **simulated** for the MVP |
| Existing model? | 🟡 Yellow | Standard demand forecasting is easy; the shortage-risk classifier must be trained on ANSM history — label quality to audit |
| Latency OK? | 🟢 Green | Daily batch — latency is irrelevant |
| Compliance / ethics? | 🟢 Green | No personal data processed (see governance.md) |
| Testable in 2–4 weeks? | 🟢 Green | Yes, on simulated stock |

→ **0 red, 2 yellow: prototype.**

---

## 8. Do-nothing baseline

**The do-nothing is not zero — it is DP-Ruptures.** The Ordre des pharmaciens already runs a free service built into most LGOs: when a pharmacy has been unable to get a drug for **72 hours**, a shortage report is created automatically and sent to the lab, which can answer with a cause and an expected return date.

What it does **not** do — and where Hygisense sits:

| | DP-Ruptures (do-nothing) | Hygisense |
|---|---|---|
| Trigger | 72 h *after* the pharmacy failed to get the drug | A **predicted** lab shortage, weeks before — while the pharmacy still has stock and can still order |
| Output | A report to the lab | A decision: **buy ahead (how many boxes) or not** |
| Uses the pharmacy's own stock and sales | No | Yes — days of stock left, with a range |
| Lists substitutable generics in stock elsewhere | No | Yes, from the official generic register |
| Price | Free | €99/month subscription |

Even with DP-Ruptures, pharmacists report **~10 h/week** (measured, PGEU) × **€40/h** (analogy) × **47 weeks** ≈ **€19k per pharmacy per year** of qualified time — before the sales lost and the patients who go elsewhere for good. The do-nothing trajectory also improves on its own: ANSM winter plans and mandatory stocks may cut shortage hours (we assume −5 %/year in 02_sizing.xlsx).

**Competitor to watch:** any LGO vendor (or the Ordre itself) adding a "days of stock left" view to DP-Ruptures would erase most of our edge. That is the main strategic risk in the memo.

---

## Sources

- ANSM, *Rapport d'activité 2025* — key figures and annexes: https://ansm.sante.fr/actualites/lansm-publie-son-rapport-dactivite-2025
- ANSM, *Rapport d'activité 2024*: https://ansm.sante.fr/actualites/impression/5452
- PGEU survey on shortages in community pharmacies (2024–25), reported by Caisse d'Épargne Pro: https://www.caisse-epargne.fr/professionnels/conseils/pharmaciens-ruptures-medicaments
- PGEU survey 2022, reported by the Ordre des pharmaciens: https://www.ordre.pharmacien.fr/les-communications/focus-sur/les-actualites/ruptures-d-approvisionnement-dans-les-officines-europeennes-des-repercussions-majeures
- Number of pharmacies, Panorama 2024 (Le Quotidien du pharmacien): https://www.lequotidiendupharmacien.fr/exercice-pro/demographie-officinale-le-nombre-de-pharmacies-continue-diminuer
- DP-Ruptures, how it works (Ordre des pharmaciens): https://www.ordre.pharmacien.fr/je-suis/pharmacien/je-suis-pharmacien-adjoint-d-officine-et-autres-exercices/mon-exercice-professionnel/le-dp-en-pratique-officine
- DP-Ruptures, connected pharmacies (Ordre des pharmaciens): https://apiop.ordre.pharmacien.fr/content/view/full/456447
