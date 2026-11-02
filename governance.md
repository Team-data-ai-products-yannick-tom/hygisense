# Governance — Drug-shortage copilot

> Team TYN · provisional answers (S1), to be revised at each session.

## 01 — Which EU AI Act tier?

**Minimal risk.** The system forecasts demand, scores the risk of a lab shortage and recommends whether to buy ahead, for a professional who validates every order. It does not diagnose, prescribe, or decide access to care. It is **not** a medical device: it never makes a recommendation about a patient's treatment.

**Watch-out:** if a future version suggested a *therapeutic* alternative (another molecule), it would move closer to medical-device territory. That stays out of scope: we only list generics from the official generic register, which the pharmacist is already legally entitled to substitute.

## 02 — Whose data, on what legal basis?

| Data | Personal? | Basis / note |
|---|---|---|
| ANSM shortage list, generic register, public drug database | No | Public open data |
| Pharmacy stock and sales history, **aggregated per product per day** | No | Business data of the pharmacy (contract with the pharmacy) |
| Patient identity, prescriptions, dispensing history per patient | **Yes — health data (GDPR art. 9)** | **Never collected.** The stock export is aggregated before it reaches the system |
| Pharmacist account (name, email) | Yes, ordinary | Contract (GDPR art. 6(1)(b)); minimal |

**Design rule:** the system ingests **quantities per product**, never per patient. GDPR therefore only applies to the pharmacist's own account data.

**Cross-tenant leakage:** pharmacy A's stock must never be visible to pharmacy B (competitors). Data isolated per pharmacy; any cross-pharmacy benchmark only on aggregated, anonymised figures.

## 03 — Who is accountable — where is the human?

- **The pharmacist** validates every order and every substitution. The system never sends an order on its own (level L2 on ordering).
- **Named owner on our side:** the product owner (to name within the team) for alert quality and model drift.
- **Override switch:** the pharmacist can mute a product, an alert type, or the whole tool; the LGO keeps working as before.

## 04 — What must it never do?

1. **Never place an order without the pharmacist's validation.**
2. **Never suggest a non-substitutable alternative** (a different molecule) — only generics from the official register.
3. **Never ingest patient-level data.**
4. Never present a forecast as a certainty: every stock-out date comes with a range, every shortage risk with its main reasons.
5. **Never recommend hoarding.** A buy-ahead is capped (base: 4 extra weeks of the pharmacy's normal demand) and never exceeds a quota set by ANSM or the wholesaler (contingentement). If every pharmacy over-buys at the first signal, the tool **creates** the shortage it predicts — a public-health risk, and the classic bullwhip effect.

## 05 — Explainable to whom?

| Audience | Explanation |
|---|---|
| Pharmacist | "You have 6 days of stock (range 4–9), based on your last 8 weeks of sales; ANSM announced a risk on 12/10; source link." |
| Our team | Logs of each alert: which data, which forecast, whether the pharmacist acted on it |
| Auditor / ANSM | The data sources used and proof that no personal data is processed |

## 06 — What happens to those it cannot serve?

- **Shortages with no warning sign** in public data (sudden factory stop): the risk model sees nothing → counter-metric: share of stock-outs **not** anticipated.
- **Pharmacies whose LGO cannot export stock:** they get a degraded mode (ANSM alerts on a list of products they enter by hand).
- **Patients:** if the tool misses a shortage, the patient is no worse off than today (do-nothing). The risk is **false reassurance** — a pharmacist who stops checking by himself. → Monitor it and say it in onboarding.

## Cost of error (S2 line) — and its owner

| Error | Cost | Type | Owner |
|---|---|---|---|
| Missed shortage (false negative) | A patient without treatment; lost sale | **Reputational / health** | Product owner |
| False alarm (false positive) | Pharmacy buys ahead for nothing: cash tied up, possible expiry | Financial | Product owner |
| Collective over-buying | Many pharmacies buy ahead at once and drain the wholesaler | **Public health / reputational** | Product owner — capped by guardrail 04-5 |
| Wrong generic suggested | Dispensing error | **Legal / health** — highest | Product owner + pharmacist validation (guardrail 04-2) |

The governance line from S2: the most expensive error, **a non-substitutable product shown as a substitute**, is a **legal and health** risk before being a financial one (priced in 02_sizing.xlsx as 2 % × €150k a year in the base case). It is owned by the **product owner**, and blocked by a rule (rung 1), not by the model.

---

## Session 3 — Data governance and trust level per step

### Data sources (datasheet summary)

| Source | Provenance | Legal basis | Purpose | Retention | Known gaps |
|---|---|---|---|---|---|
| ANSM list of shortages and shortage risks | Public website, scraped daily | Public open data | Detect shortage signals | 2 years (for the backtest) | Only drugs of major therapeutic interest are reported to ANSM; dates are publication dates, not the real start of the tension |
| Generic register (répertoire des génériques, ANSM) and public drug database (BDPM) | Public open data, monthly file | Public open data | Map a product to its substitutable generics | Latest version + history of versions | Register is updated with a lag; a newly listed generic may be missing |
| Lab / wholesaler notices (free text) | Received by the pharmacy, forwarded to the tool | Contract with the pharmacy | Extract expected return dates | 1 year | Heterogeneous formats; some notices never arrive |
| Pharmacy stock and sales, **aggregated per product per day** | Export from the LGO | Contract with the pharmacy (GDPR does not apply: no personal data) | Days-of-stock forecast | 2 years rolling | Seasonality only learnable after 1 year of history; new pharmacies have none |
| **For the MVP:** simulated stock and sales | Generated by the team | n/a | Prototype and eval-set | Course duration | Simulated demand is smoother than reality — say so at the oral |

**Isolation between customers:** each pharmacy's stock is stored and queried under its own tenant. A summary for pharmacy A must never use pharmacy B's stock (they are competitors). Any network-wide figure ("12 pharmacies near you report this shortage") is aggregated and only shown above a minimum of 5 pharmacies.

**What we do not collect, by design:** prescriptions, patient identities, dispensing per patient. The LGO export is aggregated **before** it leaves the pharmacy.

**Labels of the risk model:** "shortage" = a product listed by ANSM as in shortage. ANSM lists mainly drugs of major therapeutic interest, so shortages of other drugs are under-labelled → the model is weaker on them; say so.

**Who is in the data (the Amazon question):** the demand forecast learns from past sales. Rural or small pharmacies sell fewer units, so their forecasts are noisier. → Check the anticipation rate **by pharmacy size** on the eval-set before shipping, not only the average.

### Trust level per step (to-be process)

| Step | Who / what | Trust level | Why |
|---|---|---|---|
| 1. Fetch ANSM list and generic register | Automation (rung 1) | **L4** | Deterministic, public data, easy to check |
| 2. Match signals with the pharmacy's stock (by product code and molecule) | Rule (rung 1) | **L4** | Exact join; a mismatch is logged |
| 3a. Forecast demand → date the pharmacy's stock runs out | Classical ML, time series (rung 2) | **L3** — shown with a range; the team samples forecasts weekly | Wrong forecast = wrong timing, recoverable |
| 3b. Score the risk of a lab shortage (next 4–8 weeks) | Classical ML, classification (rung 2) | **L3** — shown with its top reasons ("3 past shortages, 1 supplier left, ANSM risk signal") | Probabilistic; errors cost money, not health, if 04-5 holds |
| 3c. Decide: buy ahead or not, how many boxes | Rule on 3a × 3b, capped (rung 1) | **L2** — a recommendation the pharmacist validates | Money and stock are at stake |
| 4. Read free-text notices (expected return date) | LLM (rung 3) | **L2** — extracted date shown with the source quote | Free text; errors must be visible |
| 5. List substitutable generics | Rule on the official register (rung 1) | **L1** — suggestion only; the pharmacist decides | Highest cost of error (legal / health) |
| 6. Draft the reorder | Automation | **L2** — the pharmacist validates every line | Money and stock are at stake |
| 7. Send the order | **Pharmacist only** | — | The way back to a person is the default |
