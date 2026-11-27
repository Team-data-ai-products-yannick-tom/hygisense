"""Build prototype/app.html — the Hygisense app (French UI), one self-contained page.

Everything shown comes from the pipeline: real drugs and ANSM declarations (BDPM), US shortages
(FDA), epidemics (Réseau Sentinelles) and their 4-week forecast; the pharmacy (assortment, stock,
sales) is simulated. Five screens: Commande · Vigilance · Rapports · Paramètres · Méthode.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from hygisense import forecast, risk, signals
from hygisense.decide import Decision, decide

DATA_DIR = Path(__file__).parent / "data"

ROOT = Path(__file__).parent
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
        "octobre", "novembre", "décembre"]
RESP = ("J01", "R03", "R05", "R01", "R06", "J05", "N02")

# Parapharmacy: no ANSM shortage follow-up (not medicines) — simulated assortment, normal reorder only
PARA = [("Crème hydratante visage 50 ml", "Avène", 18.9, 0.6), ("Eau thermale spray 300 ml", "Avène", 12.5, 0.9),
        ("Lait solaire SPF50 200 ml", "La Roche-Posay", 22.9, 0.4), ("Baume lèvres", "Uriage", 5.9, 1.1),
        ("Gel douche surgras 500 ml", "Mustela", 9.9, 0.5), ("Shampooing antipelliculaire", "Ducray", 11.5, 0.4),
        ("Sérum physiologique 40 unidoses", "Gifrer", 3.9, 2.4), ("Pansements assortis x20", "Urgo", 4.5, 0.8),
        ("Thermomètre digital", "Omron", 14.9, 0.1), ("Brosse à dents souple", "Elgydium", 4.2, 0.7),
        ("Dentifrice gencives 75 ml", "Parodontax", 5.5, 0.9), ("Gel hydroalcoolique 100 ml", "Gifrer", 3.2, 1.3),
        ("Lait infantile 1er âge 800 g", "Gallia", 21.9, 0.7), ("Mouche-bébé", "Physiolac", 6.9, 0.3),
        ("Spray nasal eau de mer", "Stérimar", 8.9, 1.2), ("Pastilles gorge miel citron", "Humex", 6.5, 1.0),
        ("Vitamine D3 gouttes", "ZymaD", 7.5, 0.6), ("Complément magnésium x60", "Arkopharma", 12.9, 0.5),
        ("Crème mains réparatrice", "Neutrogena", 6.9, 0.8), ("Préservatifs x12", "Durex", 11.9, 0.4),
        ("Test de grossesse", "Clearblue", 12.9, 0.3), ("Bas de contention classe 2", "Sigvaris", 39.0, 0.1),
        ("Huile de massage bébé", "Weleda", 13.9, 0.2), ("Coton démaquillant x80", "Demak'Up", 2.9, 0.9)]


def fr_date(d) -> str:
    return f"{JOURS[d.dayofweek]} {d.day} {MOIS[d.month - 1]} {d.year}"


def short(name: str) -> tuple[str, str]:
    """'OLANZAPINE EG 7,5 mg, comprimé' -> ('OLANZAPINE EG 7,5 mg', 'comprimé') - split on ', ' + lowercase."""
    import re
    p = re.split(r",\s+(?=[a-zéèêàâîôûç])", name, maxsplit=1)
    return p[0].strip(), (p[1].strip() if len(p) > 1 else "")


def build(out, cases, prod, sf, ev, model, run_large, fda=None, epi=None, epi_models=None,
          epi_local=None, local_models=None, reg=None):
    r, ph, sales = run_large
    info = prod.set_index("product_id")
    ids = list(ph.product_id)
    recs = r["recs"]
    # "today" = the busiest morning of the last 90 days of the test window (most BUY lines)
    recent = recs[recs.day >= recs.day.max() - pd.Timedelta(days=90)]
    day = recent.groupby("day").size().idxmax()
    sfp = sf[sf.product_id.isin(ids)].reset_index(drop=True)
    f = risk.features_on(day, sfp, ev).set_index("product_id")
    dem, std = forecast.predict(sales, day)
    stock = r["stock_path"].loc[day]
    fill = r["fill"].loc[day]
    declared = r["declared"].loc[day]
    idx_all = pd.Series(model.index(f.reset_index()), index=f.index)
    prob_all = pd.Series(model.predict(f.reset_index()), index=f.index)
    watch = out["risk_model"]["watch_threshold"]

    # epidemic adjustment of the normal reorder for respiratory / anti-infective / analgesic classes
    epi_info, epi_ratio = {}, 1.0
    if epi is not None and epi_models:
        for ind, em in epi_models.items():
            s = epi[ind].dropna()
            s = s[s.index <= day]
            now = float(s.iloc[-1])
            fc = em.predict(s.index[-1])
            hist = s.tail(60)
            past = {t: em.predict(t - pd.Timedelta(weeks=4)) for t in hist.index[8:]}
            epi_info[ind] = {"weeks": [str(t.date()) for t in hist.index], "values": [float(v) for v in hist.values],
                             "fc_weeks": [str(t.date()) for t in past], "fc_values": [round(v, 1) for v in past.values()],
                             "now": now, "next": round(fc, 1),
                             "next_week": str((s.index[-1] + pd.Timedelta(weeks=4)).date())}
        g = epi_info.get("ira") or epi_info.get("grippe")
        epi_ratio = float(np.clip(g["next"] / max(g["now"], 1), 1.0, 1.4))
    epi_scope, epi_national, regions = "France", None, []
    if epi_local is not None and local_models:
        # the pharmacy's own region drives its reorder; France stays shown for comparison
        epi_national = {k: {"now": v["now"], "next": v["next"]} for k, v in epi_info.items()}
        for ind, em in local_models.items():
            s = epi_local[ind].dropna()
            s = s[s.index <= day]
            hist = s.tail(60)
            past = {t: em.predict(t - pd.Timedelta(weeks=4)) for t in hist.index[8:]}
            epi_info[ind] = {"weeks": [str(t.date()) for t in hist.index], "values": [float(v) for v in hist.values],
                             "fc_weeks": [str(t.date()) for t in past], "fc_values": [round(v, 1) for v in past.values()],
                             "now": float(s.iloc[-1]), "next": round(em.predict(s.index[-1]), 1),
                             "next_week": str((s.index[-1] + pd.Timedelta(weeks=4)).date())}
        g = epi_info.get("ira") or epi_info.get("grippe")
        epi_ratio = float(np.clip(g["next"] / max(g["now"], 1), 1.0, 1.4))
        epi_scope = "Île-de-France"
        ind = "ira" if "ira" in local_models else "grippe"
        for code, grp in reg[reg.indicator == ind].groupby("region"):
            s = grp.set_index("date").inc100.sort_index()
            s = s[s.index >= "2009-01-01"]
            s = s.groupby(level=0).mean().dropna()       # week 53 is folded into week 52
            if s.index.min() > pd.Timestamp("2022-01-01"):
                continue
            try:
                m = signals.EpidemicModel(s.dropna()).fit(pd.Timestamp("2024-01-01"))
            except np.linalg.LinAlgError:        # region without enough past weeks
                continue
            s2 = s[s.index <= day]
            now, nxt = float(s2.iloc[-1]), float(m.predict(s2.index[-1]))
            regions.append({"name": str(grp["name"].iloc[0]), "code": int(code), "now": round(now), "next": round(nxt),
                            "boost": round((float(np.clip(nxt / max(now, 1), 1.0, 1.4)) - 1) * 100)})
        regions.sort(key=lambda x: (-x["boost"], -x["next"]))
    elif (DATA_DIR / "hyg_sentinelles_regional_summary.json").exists():
        # same model, run region by region (see data/README.md); used when the raw regional CSVs are absent
        js = json.loads((DATA_DIR / "hyg_sentinelles_regional_summary.json").read_text())
        epi_national = {k: {"now": v["now"], "next": v["next"]} for k, v in epi_info.items()}
        for ind in ("ira", "grippe"):
            r11 = js[ind]["11"]
            wk = pd.date_range(r11["hist_start"], periods=len(r11["hist"]), freq="7D")
            fc = [(str(w.date()), v) for w, v in zip(wk, r11["fc"]) if v is not None]
            epi_info[ind] = {"weeks": [str(w.date()) for w in wk], "values": r11["hist"],
                             "fc_weeks": [w for w, _ in fc], "fc_values": [v for _, v in fc],
                             "now": r11["now"], "next": r11["next"],
                             "next_week": str((wk[-1] + pd.Timedelta(weeks=4)).date()), "mae": r11["mae"]}
        g = epi_info["ira"]
        epi_ratio = float(np.clip(g["next"] / max(g["now"], 1), 1.0, 1.4))
        epi_scope = "Île-de-France"
        for code, rg in js["ira"].items():
            regions.append({"name": rg["name"].replace("-", " ").title(), "code": int(code), "now": round(rg["now"]),
                            "next": round(rg["next"]),
                            "boost": round((float(np.clip(rg["next"] / max(rg["now"], 1), 1.0, 1.4)) - 1) * 100)})
        regions.sort(key=lambda x: (-x["boost"], -x["next"]))

    def alts(pid):
        g = info.at[pid, "group_id"] if "group_id" in info.columns else None
        if not isinstance(g, str):
            return []
        same = prod[(prod.group_id == g) & (prod.product_id != pid)].drop_duplicates("holder").head(8)
        return [{"id": a.product_id, "name": short(a.name)[0], "holder": a.holder.title(),
                 "price": None if pd.isna(a.price) else round(float(a.price), 2)} for a in same.itertuples()]

    def base(pid):
        n, form = short(info.at[pid, "name"])
        price = info.at[pid, "price"]
        dl, lo, hi = forecast.days_left(float(stock[pid]), float(dem[pid]), float(std[pid]))
        return {"id": pid, "name": n, "form": form, "holder": info.at[pid, "holder"].title(),
                "price": None if pd.isna(price) else round(float(price), 2), "stock": int(stock[pid]),
                "demand": round(float(dem[pid]), 2), "days": dl, "kind": "med"}

    anticip, reassort = [], []
    for pid in ids:
        if declared[pid] and fill[pid] == 1.0:
            dec = decide(float(stock[pid]), float(dem[pid]), 365, 0.95, "none", watch_threshold=watch)
            if dec.decision == "BUY":
                e = ev[(ev.product_id == pid) & (ev.start <= day)].tail(1).iloc[0]
                row = base(pid)
                row.update({"index": round(float(idx_all[pid]), 1), "reasons": model.reasons(f.loc[pid]),
                        "prob": round(float(prob_all[pid]) * 100, 1),
                            "qty": dec.buy_qty, "cap": dec.cap, "status": e.status,
                            "since": f"{e.start.day:02d}/{e.start.month:02d}/{e.start.year}",
                            "left": int(14 - (day - e.start).days), "link": e.ansm_link, "alts": alts(pid)})
                anticip.append(row)
                continue
        if fill[pid] == 1.0 and dem[pid] > 0 and stock[pid] < max(dem[pid] * 7, 1):
            target = max(np.ceil(dem[pid] * 14), 2)
            boost = epi_ratio if info.at[pid, "atc3"] in RESP else 1.0
            qty = int(np.ceil((target - stock[pid]) * boost))
            if qty > 0:
                row = base(pid)
                row.update({"qty": qty, "epi": round((boost - 1) * 100) if boost > 1 else 0, "alts": alts(pid)})
                reassort.append(row)
    anticip.sort(key=lambda x: (x["left"], -x["qty"]))
    reassort.sort(key=lambda x: (x["days"] if x["days"] is not None else 99))

    # parapharmacy (simulated): stock, sales, normal reorder
    rng = np.random.default_rng(5)
    para = []
    for i, (n, brand, price, dmd) in enumerate(PARA):
        st = int(rng.integers(0, int(dmd * 20) + 3))
        row = {"id": f"PARA{i:03d}", "name": n, "form": "Parapharmacie", "holder": brand, "price": price,
               "stock": st, "demand": dmd, "days": round(st / dmd, 1), "kind": "para", "alts": []}
        para.append(row)
        if st < dmd * 7:
            reassort.append({**row, "qty": int(np.ceil(dmd * 14 - st)), "epi": 0})

    # catalogue for the "add a product" search: the pharmacy's references + parapharmacy
    catalogue = []
    for pid in ids:
        n, form = short(info.at[pid, "name"])
        p = info.at[pid, "price"]
        catalogue.append([pid, n, form[:40], info.at[pid, "holder"].title()[:28],
                          None if pd.isna(p) else round(float(p), 2), int(stock[pid]), round(float(dem[pid]), 2)])
    for row in para:
        catalogue.append([row["id"], row["name"], "Parapharmacie", row["holder"], row["price"], row["stock"], row["demand"]])

    # vigilance list: every product of the pharmacy with its index
    vig = []
    us_active = set()
    if fda is not None:
        act = fda[(fda.start <= day) & (fda.end > day)]
        us_active = set(act.stem)
        us_since = act.groupby("stem").start.min()
    for pid in ids:
        if fill[pid] < 1.0 and not declared[pid]:
            state = "rupture"          # already short at the wholesaler
        elif declared[pid]:
            state = "declaree"
        else:
            state = "vigilance"
        n, form = short(info.at[pid, "name"])
        stm = f.at[pid, "stem"]
        us = None
        if stm in us_active:
            d0 = us_since[stm]
            us = f"{d0.month:02d}/{d0.year}"
        dl, _, _ = forecast.days_left(float(stock[pid]), float(dem[pid]), float(std[pid]))
        vig.append({"id": pid, "name": n, "form": form, "holder": info.at[pid, "holder"].title(),
                    "index": round(float(idx_all[pid]), 2), "prob": round(float(prob_all[pid]) * 100, 2),
                    "reasons": model.reasons(f.loc[pid]), "state": state, "us": us,
                    "stock": int(stock[pid]), "days": dl})
    vig.sort(key=lambda x: ({"declaree": 0, "vigilance": 1, "rupture": 2}[x["state"]], -x["index"]))

    # ---- proof: shortages seen coming BEFORE the ANSM declaration (test 2026, this pharmacy)
    mr = r["model_risk"]
    thr_ph = float(np.nanquantile(mr.values, 0.90))      # top 10 % of this pharmacy's products
    proof, caught = [], 0
    evw = ev[ev.product_id.isin(ids) & (ev.start >= mr.index.min() + pd.Timedelta(days=56))]
    for e in evw.sort_values("start").itertuples():
        w = mr.loc[e.start - pd.Timedelta(days=56):e.start - pd.Timedelta(days=7), e.product_id]
        hit = w[w >= thr_ph]
        n, form = short(info.at[e.product_id, "name"])
        item = {"name": n, "form": form, "status": e.status, "declared": str(e.start.date()), "seen": None, "lead": 0,
                "reasons": []}
        if len(hit):
            caught += 1
            t0 = hit.index.min()
            f0 = risk.features_on(t0, sf[sf.product_id == e.product_id].reset_index(drop=True), ev).set_index("product_id")
            item.update({"seen": str(t0.date()), "lead": int((e.start - t0).days),
                         "reasons": model.reasons(f0.loc[e.product_id])})
        proof.append(item)
    proof_summary = {"declarations": len(proof), "caught": caught,
                     "flag_share": round(float((mr >= thr_ph).mean().mean()), 3),
                     "random_expected": round(len(proof) * float((mr >= thr_ph).mean().mean()), 1)}

    # ---- preventive candidates on the demo morning: high vigilance, no announcement yet
    prev = []
    for pid in ids:
        if declared[pid] or fill[pid] < 1.0 or dem[pid] <= 0:
            continue
        if float(r["model_risk"].at[day, pid]) >= thr_ph:
            row = base(pid)
            row.update({"index": round(float(idx_all[pid]), 1), "reasons": model.reasons(f.loc[pid]), "prob": round(float(prob_all[pid]) * 100, 1),
                        "qty": int(max(1, np.ceil(dem[pid] * 14))), "alts": alts(pid)})
            prev.append(row)
    prev.sort(key=lambda x: (-x["index"], x["days"] if x["days"] is not None else 99))
    prev = prev[:8]

    # reports: simulated sales x public price
    price = info.price.reindex(ids).fillna(info.price.median())
    daily_ca = (sales[ids] * price.values).sum(axis=1)
    daily_box = sales[ids].sum(axis=1)
    para_ca = sum(p[2] * p[3] for p in PARA)
    lost = ((r["stock_path"] <= 0) & (r["fill"] < 1)).astype(int) * sales.loc[r["stock_path"].index, ids]

    def period(days):
        a, b = day - pd.Timedelta(days=days - 1), day
        pa, pb = a - pd.Timedelta(days=days), a - pd.Timedelta(days=1)
        ca = float(daily_ca[a:b].sum() + para_ca * days)
        ca_prev = float(daily_ca[pa:pb].sum() + para_ca * days)
        top = (sales.loc[a:b, ids].sum() * price.values).sort_values(ascending=False).head(8)
        evp = r["events"]
        evp = evp[(evp.start >= a) & (evp.start <= b)] if len(evp) else evp
        n_decl = int(((ev.product_id.isin(ids)) & (ev.start >= a) & (ev.start <= b)).sum())
        recp = r["recs"][(r["recs"].day >= a) & (r["recs"].day <= b)]
        lost_p = lost.loc[a:b].sum()
        miss = lost_p[lost_p > 0].sort_values(ascending=False).head(6)
        return {
            "from": str(a.date()), "to": str(b.date()), "ca": round(ca), "ca_prev": round(ca_prev),
            "boxes": int(daily_box[a:b].sum()), "margin": round(ca * 0.25),
            "lost_boxes": int(lost_p.sum()), "declarations": n_decl, "emptying": int(len(evp)),
            "anticipated": int(evp.anticipated.sum()) if len(evp) else 0,
            "buy_lines": int(recp.product_id.nunique()),
            "top": [{"name": short(info.at[p, "name"])[0], "ca": round(float(v))} for p, v in top.items()],
            "missing": [{"name": short(info.at[p, "name"])[0], "boxes": int(v)} for p, v in miss.items()],
        }

    weeks = []
    for k in range(11, -1, -1):
        b = day - pd.Timedelta(days=7 * k)
        a = b - pd.Timedelta(days=6)
        weeks.append({"week": f"{a.day:02d}/{a.month:02d}", "ca": round(float(daily_ca[a:b].sum() + para_ca * 7))})

    data = {
        "pharmacy": "Pharmacie des Lilas", "today": fr_date(day), "today_iso": str(day.date()),
        "anticip": anticip, "reassort": reassort, "prev": prev, "proof": proof, "proof_summary": proof_summary, "catalogue": catalogue, "vigilance": vig,
        "epi": epi_info, "epi_ratio": round(epi_ratio, 2), "epi_scope": epi_scope, "epi_national": epi_national,
        "regions": regions,
        "report": {"week": period(7), "month": period(30), "weeks": weeks},
        "cases": cases.to_dict(orient="records"), "R": out,
    }
    html = TEMPLATE.replace("/*DATA*/null", json.dumps(data, default=str, ensure_ascii=False))
    (ROOT / "prototype").mkdir(exist_ok=True)
    (ROOT / "prototype" / "app.html").write_text(html, encoding="utf-8")


TEMPLATE = (Path(__file__).parent / "prototype" / "app_template.html").read_text(encoding="utf-8") \
    if (Path(__file__).parent / "prototype" / "app_template.html").exists() else "/*DATA*/null"
