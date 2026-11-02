# 03 — Prototype link · Hygisense

**Clickable prototype:** https://claude.ai/artifact/WgBRoNJX8kFztdCaHnR814
(source: `prototype/hygisense_prototype.html` — open it locally in a browser if the link is not shared with you yet)

**What it is:** the pharmacist's morning screen inside the LGO — for each product at risk, a decision (**buy N boxes now / watch / don't buy**) with its reasons, the lab-shortage risk, the days of stock left with a range, the generics fallback, and a draft order the pharmacist validates. **Simulated data** (taken from `evals/cases_v0.csv`).

**What it is not:** the S4 prototype (Streamlit, runs the real logic on the eval-set), nor production code. Nothing is sent to a wholesaler.

**Built with:** a Claude artifact, from the three first paragraphs of 03_product_brief.md, in under an hour.

## Test task (20 minutes, think aloud, don't help)

"It is 8:30, you open the pharmacy. Using this screen, decide what you will buy ahead today, and tell us one recommendation you would refuse and why."

## Users who tried it

| # | Profile | Finished without help? | Where they hesitated | What they expected | Changed in brief v2 |
|---|---|---|---|---|---|
| 1 | | | | | |
| 2 | | | | | |
