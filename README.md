# Hygisense — drug-shortage copilot for community pharmacies

Team **TYN** — Tom, Yannick, Nissrine · Albert School · Data & AI Product (MSA-DAT07-04), 2026–27

**In one sentence:** every morning, for every product, Hygisense forecasts when the pharmacy's stock will run out (ML on demand) and how likely the lab is to go short in the next 8 weeks (ML on public data), and recommends **buying N boxes ahead now, or not** — the pharmacist validates every order.

**Decision so far:** conditional go — launch only if a groupement pilot shows ≥ 15 % adoption and the backtest shows Hygisense says "buy ahead" in time for ≥ 25 % of past shortages (see `02_sizing.xlsx`).

| Session | File | Status |
|---|---|---|
| S1 Diagnosis | `01_problem_statement.md` · `governance.md` | done |
| S2 Sizing | `02_sizing.xlsx` · `02_investment_memo.md` | done |
| S3 MVP design | `03_product_brief.md` (v1) · `03_ai_lean_canvas.md` · `03_user_research.md` · `03_prototype_link.md` · `spec.md` · `evals/cases_v0.csv` | v1 done — **user interviews and brief v2 to do** |
| S4 Build & decode | `/prototype` (Streamlit) · `evals/report_v0.md` · `04_architecture.md` | to do |
| S5 Metrics | `05_metrics.md` · eval-set v1 | to do |
| S6 Experiments | `06_ab_protocol.md` | to do |
| S7 Operation | `07_operations.md` | to do |
| S8 Launch | `08_launch_memo.md` · tag v1.0 | to do |

**Data:** public ANSM and generic-register data; pharmacy stock is **simulated**. No patient data is ever processed (see `governance.md`).
**Company:** Hygisense is a fictional start-up that sells the product of the same name to pharmacies (€99/month).
