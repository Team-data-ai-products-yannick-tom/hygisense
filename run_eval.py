"""Run the whole evaluation and rebuild the demo page.

    python run_eval.py      # a few minutes; needs the 6 BDPM files in data/ (see data/README.md)

Writes evals/report_numbers.json, evals/cases_v0_results.csv, evals/backtest_events.csv,
prototype/app.html. Order matters - nothing is tuned on the test window:
1. 20 decision cases (evals/cases_v0.csv): the rule and its guardrails.
2. Risk model: trained on 2024 - early 2025, thresholds read on a validation window (2025),
   retrained, then scored once on the frozen test window (2026).
3. Backtest of the whole product on two simulated pharmacies, test window only.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from hygisense import backtest, bdpm, catalog, forecast, risk, signals, vigilance
from hygisense.decide import BUY_THRESHOLD, decide

ROOT = Path(__file__).parent
SNAPSHOT = pd.Timestamp("2026-11-19")          # date of the BDPM files used
REGION = 11                                     # Ile-de-France (Sentinelles old-region code) - demo pharmacy
TRAIN = (pd.Timestamp("2024-01-01"), pd.Timestamp("2025-03-01"))
VALID = (pd.Timestamp("2025-03-29"), pd.Timestamp("2025-11-01"))
TEST = (pd.Timestamp("2026-01-01"), SNAPSHOT)
CRITERION, PRODUCT_GATE = 0.25, 0.21


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(v) else v


def eval_cases() -> pd.DataFrame:
    c = pd.read_csv(ROOT / "evals" / "cases_v0.csv")
    out = []
    for r in c.itertuples(index=False):
        d = dict(zip(c.columns, r))
        quota = num(d["quota_boxes"])
        dec = decide(stock=float(d["stock_units"]), demand=num(d["forecast_daily_demand"]),
                     history_days=int(d["sales_history_days"]),
                     risk=float(d["shortage_risk_8w (model output, simulated)"]),
                     status=d["ansm_status"], quota=int(quota) if quota else None,
                     network_freeze=d["network_freeze"] == "yes",
                     notice_text=d["notice_text"] if isinstance(d["notice_text"], str) else None)
        exp = d["expected_decision"].split(" (")[0]
        out.append({"case": d["case_id"], "product": d["product (simulated)"], "edge_case": d["edge_case"],
                    "expected": f'{exp} {d["expected_buy_qty"]}', "got": f"{dec.decision} {dec.buy_qty}",
                    "why": dec.why, "pass": dec.decision == exp and dec.buy_qty == int(d["expected_buy_qty"])})
    return pd.DataFrame(out)


def topk(y, p, share=0.01):
    k = max(int(len(p) * share), 1)
    idx = np.argsort(-p)[:k]
    prec = float(np.asarray(y)[idx].mean())
    return {"precision": round(prec, 4), "recall": round(float(np.asarray(y)[idx].sum() / max(y.sum(), 1)), 3),
            "base_rate": round(float(np.mean(y)), 4), "lift": round(prec / max(float(np.mean(y)), 1e-9), 1)}


def forecast_error(sales, start, end):
    res = {"mean_56d": [], "seasonal": []}
    for d in pd.date_range(start, end - pd.Timedelta(days=14), freq="7D"):
        actual = sales.loc[d + pd.Timedelta(days=1):d + pd.Timedelta(days=14)].mean()
        res["mean_56d"].append((forecast.naive(sales, d) - actual).abs().sum() / actual.sum())
        res["seasonal"].append((forecast.seasonal(sales, d)[0] - actual).abs().sum() / actual.sum())
    return {k: round(float(np.mean(v)), 3) for k, v in res.items()}


def summarise(r, size, n_products):
    e = r["events"]
    rate = lambda s: round(float(s.mean()), 3) if len(s) else None
    return {
        "pharmacy": size, "references": n_products,
        "declarations_on_its_products": int(r["n_declarations"]),
        "declarations_that_empty_the_shelf": int(len(e)),
        "anticipated": int(e.anticipated.sum()), "anticipation_rate": rate(e.anticipated),
        "anticipated_before_the_declaration": int(e.before_declaration.sum()),
        "rate_tension": rate(e[e.status == "tension"].anticipated),
        "rate_rupture": rate(e[e.status == "rupture"].anticipated),
        "buy_episodes": r["episodes"], "useless_buy_episodes": r["useless"],
        "useless_share": round(r["useless"] / max(r["episodes"], 1), 3), "cap_breaches": r["cap_breaches"],
        "lost_units_do_nothing": r["lost_units_do_nothing"], "lost_units_if_followed": r["lost_units_with"],
        "lost_units_reduction": round(1 - r["lost_units_with"] / max(r["lost_units_do_nothing"], 1), 3),
    }


def main():
    cases = eval_cases()
    d = bdpm.load()
    ev, unknown = bdpm.shortage_events(d, SNAPSHOT)
    prod = catalog.products(d)
    sf = risk.static_features(prod)
    ev = risk.annotate_events(ev, sf)

    # -- external signals: FDA shortages + epidemic forecast (fitted on data before 2024 only)
    fda = signals.load_fda(SNAPSHOT)
    epi = signals.load_epidemics()
    epi_models, epi_eval, epi_fc = {}, {}, {}
    for ind in ("grippe", "ira"):
        em = signals.EpidemicModel(epi[ind]).fit(TRAIN[0])
        epi_models[ind] = em
        epi_eval[ind] = em.evaluate(pd.Timestamp("2023-07-01"), SNAPSHOT)
        idx = epi[ind].dropna().index
        epi_fc[ind] = pd.Series({t: em.predict(t) for t in idx[idx >= "2021-01-01"]})
    risk.set_external(fda, epi_fc["ira"].combine_first(epi_fc["grippe"]))

    # -- regional epidemics (Sentinelles geo=REG): the demo pharmacy is in Ile-de-France (old region 11)
    reg = signals.load_regional()
    epi_local, local_models, epi_eval_reg = None, None, {}
    if reg is not None:
        epi_local = signals.regional_series(reg, REGION)
        local_models = {}
        for ind in ("grippe", "ira"):
            if ind not in epi_local or epi_local[ind].dropna().index.min() > TRAIN[0] - pd.Timedelta(weeks=104):
                continue
            m = signals.EpidemicModel(epi_local[ind]).fit(TRAIN[0])
            local_models[ind] = m
            ev_r = m.evaluate(pd.Timestamp("2023-07-01"), SNAPSHOT)
            # what we did before: the national forecast used as is for this region
            s = epi_local[ind].dropna()
            errs = [abs(epi_models[ind].predict(d) - s[d + pd.Timedelta(weeks=4)])
                    for d in s.index[(s.index >= "2023-07-01") & (s.index <= SNAPSHOT - pd.Timedelta(weeks=4))]
                    if d + pd.Timedelta(weeks=4) in s.index and d in epi[ind].dropna().index]
            ev_r["national_model"] = round(float(np.mean(errs)), 1) if errs else None
            epi_eval_reg[ind] = ev_r

    # -- datasets: train -> validation (fit the index) -> test once
    tr = risk.build_dataset(sf, ev, *TRAIN, exclude=unknown)
    va = risk.build_dataset(sf, ev, *VALID, exclude=unknown)
    te = risk.build_dataset(sf, ev, TEST[0], SNAPSHOT - pd.Timedelta(days=risk.HORIZON), exclude=unknown)

    # v1: logistic regression (kept as the comparison)
    lr = risk.RiskModel(risk.FEATURES_BASE).fit(pd.concat([tr, va]))
    p_lr = lr.predict(te)
    # v2: vigilance index, relative risks measured on 2025 only
    vig = vigilance.VigilanceIndex().fit(va)
    p_va, p_te = vig.predict(va), vig.predict(te)
    watch_threshold = float(np.quantile(p_va, 0.90))          # top 10 % of products -> WATCH list
    flagged = p_te >= watch_threshold
    us = lambda x: (x.us_short_active > 0)
    rr_us = lambda x: round(float(x.y[us(x)].mean() / x.y[~us(x)].mean()), 2)
    model_card = {
        "rows_test": int(len(te)), "positives_test": int(te.y.sum()),
        "v1_logistic_auc_test": round(roc_auc_score(te.y, p_lr), 3),
        "v1_logistic_top1pct_test": topk(te.y.values, p_lr),
        "auc_is_mitm_alone_test": round(roc_auc_score(te.y, te.is_mitm), 3),
        "vigilance": vig.card(),
        "vigilance_auc_validation": round(roc_auc_score(va.y, p_va), 3),
        "vigilance_auc_test": round(roc_auc_score(te.y, p_te), 3),
        "vigilance_top1pct_test": topk(te.y.values, p_te, 0.01),
        "vigilance_top10pct_test": topk(te.y.values, p_te, 0.10),
        "watch_share_test": round(float(flagged.mean()), 3),
        "watch_captured_test": int(te.y[flagged].sum()),
        "us_shortage_relative_risk": {"2025": rr_us(va), "2026": rr_us(te)},
        "watch_threshold": round(watch_threshold, 5),
        "epidemic_model_mae_4w": epi_eval,
        "epidemic_model_mae_4w_ile_de_france": epi_eval_reg,
    }

    # -- backtest on two simulated pharmacies, test window only
    results, runs, sens = [], {}, []
    for size, seed in (("large", 1), ("small", 2)):
        ph = catalog.pharmacy(prod, size, seed)
        sales = catalog.sales(ph, pd.Timestamp("2024-09-01"), SNAPSHOT, seed)
        r = backtest.run(ph, sales, sf, ev, vig, *TEST, BUY_THRESHOLD, watch_threshold, buffer_days=14)
        r["n_declarations"] = int(((ev.product_id.isin(ph.product_id)) & (ev.start >= TEST[0])).sum())
        s = summarise(r, size, len(ph))
        s["forecast_wape"] = forecast_error(sales, TEST[0], SNAPSHOT)
        results.append(s)
        runs[size] = (r, ph, sales)
        if size == "large":
            for buf in (0, 7):
                rb = backtest.run(ph, sales, sf, ev, vig, *TEST, BUY_THRESHOLD, watch_threshold, buffer_days=buf)
                rb["n_declarations"] = r["n_declarations"]
                sb = summarise(rb, size, len(ph))
                sens.append({"wholesaler_buffer_days": buf, "anticipation_rate": sb["anticipation_rate"],
                             "shelf_emptying_declarations": sb["declarations_that_empty_the_shelf"]})
            sens.append({"wholesaler_buffer_days": 14, "anticipation_rate": s["anticipation_rate"],
                         "shelf_emptying_declarations": s["declarations_that_empty_the_shelf"]})

    allev = pd.concat([runs[k][0]["events"].assign(pharmacy=k) for k in runs])
    out = {
        "data": {"source": "BDPM (ANSM, HAS, UNCAM), files of November 2026; openFDA drug shortages; "
                           "Réseau Sentinelles (Inserm, Sorbonne Université)",
                 "snapshot": str(SNAPSHOT.date()), "marketed_products": int(len(prod)),
                 "ansm_declarations_used": int(len(ev)), "declarations_by_status": ev.status.value_counts().to_dict(),
                 "left_out_back_in_stock_without_start": len(unknown), "fda_records": int(len(fda)),
                 "products_matched_to_fda": round(float(sf.stem.isin(set(fda.stem)).mean()), 3)},
        "windows": {"train": [str(TRAIN[0].date()), str(TRAIN[1].date())],
                    "validation": [str(VALID[0].date()), str(VALID[1].date())],
                    "test": [str(TEST[0].date()), str(TEST[1].date())]},
        "decision_cases_passed": int(cases["pass"].sum()), "decision_cases_total": int(len(cases)),
        "risk_model": model_card,
        "anticipation_rate_overall": round(float(allev.anticipated.mean()), 3),
        "criterion": CRITERION, "product_gate": PRODUCT_GATE,
        "by_pharmacy": results, "sensitivity_wholesaler_buffer": sens,
    }
    (ROOT / "evals" / "report_numbers.json").write_text(json.dumps(out, indent=2, default=str))
    cases.to_csv(ROOT / "evals" / "cases_v0_results.csv", index=False)
    names = prod.set_index("product_id").name
    allev.assign(name=allev.product_id.map(names)).to_csv(ROOT / "evals" / "backtest_events.csv", index=False)

    from build_app import build
    build(out, cases, prod, sf, ev, vig, runs["large"], fda=fda, epi=epi, epi_models=epi_models,
          epi_local=epi_local, local_models=local_models, reg=reg)
    print(json.dumps({k: v for k, v in out.items() if k not in ("risk_model",)}, indent=1, default=str))
    print(json.dumps(model_card, indent=1))
    return out


if __name__ == "__main__":
    main()
