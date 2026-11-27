# evals/

| File | What it is | Who wrote / labelled it | Frozen? |
|---|---|---|---|
| `cases_v0.csv` | 20 decision cases for the rule: nominal, cap, quota, freeze, prompt injection, personal data in a notice, too late, no history… | the team, **before** the build (S3), expected outputs computed by hand from the rule | yes — never edited to make a run pass |
| `cases_v0_results.csv` | output of the last run on the 20 cases | `run_eval.py` | generated |
| `backtest_events.csv` | every ANSM declaration of 2026 that would have emptied a simulated pharmacy's shelf, and whether Hygisense said BUY in time | `run_eval.py`, labels = **ANSM** declarations (BDPM) | generated |
| `report_numbers.json` | all the numbers of `report_v0.md` | `run_eval.py` | generated |
| `report_v0.md` | the number against the criterion, by segment, misses, limits | the team | v0, 19 Nov 2026 |

**Where the labels come from.** A shortage = a *tension* or *rupture* declared by the lab to ANSM and published in the BDPM availability file. Nobody on the team labels shortages by hand, so there is no grader-agreement issue on the backtest. The 20 decision cases were labelled by one person and checked by a second one.

**Time split, no tuning on the test.** Model trained on Jan 2024 – Mar 2025, WATCH threshold read on Apr – Nov 2025 (validation), then retrained and scored **once** on 2026 (test). Same windows for the pharmacy backtest.

**Segments reported:** pharmacy size (large / small), declaration type (tension / rupture), anticipated before vs after the ANSM declaration.

**Eval-set size (S5: 100 cases).** 20 rule cases + 52 real shortage events in 2026 that empty a simulated shelf (31 + 21) + 117,476 product-dates (326 declarations) for the vigilance index + 3 years of weekly epidemic forecasts. To reach 100 shelf-emptying events: add pharmacies with other seeds, and the 2025 events once the history is archived.

**No LLM judge.** The MVP has no generated text to grade, and every label is either an ANSM declaration or a number from the rule. If the COULD feature (reading lab notices) is built, a rubric and a judge validated on 30 notices graded by two of us come with it.
