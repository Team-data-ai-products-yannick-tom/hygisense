# data/

## Real data — Base de données publique des médicaments (BDPM)

Source: https://base-donnees-publique.medicaments.gouv.fr/telechargement — ANSM, HAS, UNCAM, Licence Ouverte. Files downloaded on **19 November 2026** (BDPM updated monthly; the availability file is dated 3 Nov 2026).

| File | What we use it for |
|---|---|
| `bdpm_CIS_bdpm.txt` | 15,799 specialities (CIS); 12,236 marketed, homeopathy excluded = our product list |
| `bdpm_CIS_CIP_bdpm.txt` | 20,898 boxes (CIP13): price, reimbursement rate — to pick what a city pharmacy stocks |
| `bdpm_CIS_GENER_bdpm.txt` | generic groups — substitutes and the number of labs per molecule |
| `bdpm_CIS_COMPO_bdpm.txt` | active substance of each product |
| `bdpm_CIS_MITM.txt` | drugs of major therapeutic interest + ATC class |
| `bdpm_CIS_CIP_Dispo_Spec.txt` | **ANSM supply declarations**: tension (2), rupture (1), discontinuation (3), back in stock (4), with start and end dates — the labels of the backtest |

Format: tab-separated, no header, Windows-1252 except the boxes file (UTF-8). Columns: `hygisense/bdpm.py`.
Limit: the availability file is a **snapshot** (declarations still listed), not the full history since 2014. The full history is on data.ansm.sante.fr (per drug, no bulk export). From now on, archiving the file every month builds our own history.

## Real data — external signals

| File | Source | What we use it for |
|---|---|---|
| `hyg_fda_shortages_1.csv`, `hyg_fda_shortages_2.csv` | openFDA Drug Shortages API (FDA), downloaded 19 Nov 2026 — 1,585 records since 2012 | "already short in the US" flag of the vigilance index |
| `hyg_sentinelles.csv` | Réseau Sentinelles (Inserm, Sorbonne Université) API — weekly incidence per 100,000 since 2005: influenza-like illness, acute respiratory infections, acute diarrhoea | 4-week epidemic forecast |

## Simulated data

The pharmacy is simulated in `hygisense/catalog.py` (seeded, reproducible): assortment of ~3,000 (large) or ~1,800 (small) reimbursed city references, one generic per group from two partner labs, long-tail demand scaled to ≈ 6,500 € (large) / 2,600 € (small) of medicines a day, expensive drugs selling fewer boxes, winter peak for antibiotics and respiratory drugs, normal reorder up to 14 days. No patient data exists anywhere in this project.

To refresh: download the six files again into this folder and run `python run_eval.py`.

Parapharmacy items in the app are simulated too (no shortage follow-up: ANSM declarations concern medicines).

## Regional epidemics — `hyg_sentinelles_regional_summary.json`
Réseau Sentinelles, weekly incidence by region (geo=REG, the 22 former regions), acute respiratory infections (indicator 25) and influenza-like illness (3), downloaded from the sentiweb API on 27 Nov 2026. The container that runs the pipeline could not reach sentiweb, so the same 4-week model as `signals.EpidemicModel` (fit on weeks before 2024) was run region by region in the browser and its output saved here: level on the demo morning (week of 31 Aug 2026), forecast 4 weeks later, 4-week error vs persistence (Jul 2023 – Nov 2026), and 60 weeks of Île-de-France history. If the raw files `hyg_sentinelles_reg_3.csv`, `_25.csv`, `_6.csv` are put in this folder, `run_eval.py` rebuilds everything from them (`signals.load_regional`).
