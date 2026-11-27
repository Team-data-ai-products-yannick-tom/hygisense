"""From the BDPM to (1) a product table with features, (2) a plausible pharmacy.

Products are specialities (CIS) marketed in France, homeopathy excluded.
The pharmacy is SIMULATED on top of the real catalogue: which boxes it stocks,
how many it sells a day. Rules are written below so anyone can challenge them.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Routes a community pharmacy dispenses (hospital-only injectables are mostly left out)
CITY_ROUTES = ("orale", "cutanée", "inhalée", "nasale", "ophtalmique", "auriculaire", "rectale",
               "vaginale", "sublinguale", "buccale", "transdermique", "sous-cutanée")
PREFERRED_GENERIC_LABS = ("BIOGARAN", "VIATRIS", "TEVA", "SANDOZ", "EG LABO", "ARROW", "ZENTIVA", "CRISTERS")
WINTER_ATC = ("J01", "R03", "R05", "R01", "R06", "J05")


def products(d: dict) -> pd.DataFrame:
    c = d["CIS_bdpm"]
    c = c[(c.marketing == "Commercialisée") & ~c.procedure.str.contains("homéo", case=False)].copy()
    g = d["CIS_GENER_bdpm"]
    g = g.drop_duplicates("cis")
    group_size = g.groupby("group_id").cis.nunique()
    c = c.merge(g[["cis", "group_id", "generic_type"]], on="cis", how="left")
    c["in_generic_group"] = c.group_id.notna()
    c["n_in_group"] = c.group_id.map(group_size).fillna(1)
    c["is_generic"] = c.generic_type.isin(["1", "2", "4"])
    # main active substance (first SA line)
    comp = d["CIS_COMPO_bdpm"]
    sa = comp[comp.nature == "SA"].drop_duplicates("cis")[["cis", "substance_code", "substance"]]
    c = c.merge(sa, on="cis", how="left")
    c["substance_code"] = c.substance_code.fillna("cis:" + c.cis)
    # number of distinct marketing-authorisation holders for the same substance and form
    c["form_short"] = c.form.str.split().str[0].str.lower()
    key = c.substance_code + "|" + c.form_short
    c["n_holders_substance"] = key.map(c.groupby(key).holder.nunique())
    c["holder_size"] = c.holder.map(c.holder.value_counts())
    m = d["CIS_MITM"].drop_duplicates("cis")[["cis", "atc"]]
    c = c.merge(m, on="cis", how="left")
    c["is_mitm"] = c.atc.notna()
    c["atc1"] = c.atc.str[:1].fillna("?")
    c["atc3"] = c.atc.str[:3].fillna("?")
    c["oral"] = c.route.str.contains("orale")
    c["city_route"] = c.route.apply(lambda r: any(x in r for x in CITY_ROUTES))
    c["age_years"] = ((pd.Timestamp("2026-11-19") - c.amm_date).dt.days / 365.25).clip(0, 60)
    p = d["CIS_CIP_bdpm"]
    p = p[p.pack_marketing.str.contains("Déclaration de commercialisation")]
    main = p.sort_values("price", ascending=False).drop_duplicates("cis")[["cis", "cip13", "pack", "price", "reimb_rate"]]
    c = c.merge(main, on="cis", how="left")
    c["reimbursed"] = c.reimb_rate.notna()
    c["n_packs"] = c.cis.map(p.groupby("cis").size()).fillna(0)
    c = c.rename(columns={"cis": "product_id"})
    return c.reset_index(drop=True)


def pharmacy(prod: pd.DataFrame, size: str, seed: int) -> pd.DataFrame:
    """A plausible city pharmacy: ~3,000 references (large) or ~1,800 (small).

    - reimbursed, marketed, city routes only;
    - per generic group: the brand + ONE generic from the pharmacy's two partner labs if possible
      (French pharmacies concentrate generics on one or two labs);
    - demand: long tail (lognormal), generics sell ~4x the brand once substituted,
      chronic MITM drugs sell more; winter classes get seasonality in sales().
    """
    rng = np.random.default_rng(seed)
    pool = prod[prod.reimbursed & prod.city_route & prod.cip13.notna()].copy()
    partners = rng.choice(PREFERRED_GENERIC_LABS, size=2, replace=False)
    keep = []
    for gid, grp in pool[pool.in_generic_group].groupby("group_id"):
        brand = grp[grp.generic_type == "0"]
        gens = grp[grp.is_generic]
        pick = gens[gens.holder.str.upper().str.contains("|".join(partners))]
        if pick.empty and not gens.empty:
            pick = gens.sample(1, random_state=int(rng.integers(1e9)))
        keep += list(brand.product_id[:1]) + list(pick.product_id[:1])
    keep += list(pool[~pool.in_generic_group].product_id)
    ph = pool[pool.product_id.isin(keep)].copy()
    n = {"large": 3000, "small": 1800}[size]
    w = np.where(ph.is_mitm, 2.0, 1.0) * np.where(ph.in_generic_group, 1.5, 1.0)
    if len(ph) > n:
        keys = rng.random(len(ph)) ** (1 / w)          # weighted sampling without replacement
        ph = ph.iloc[np.argsort(-keys)[:n]]
    base = rng.lognormal(mean=-1.6, sigma=1.3, size=len(ph))           # median ~0.2 box/day
    base *= np.where(ph.is_generic, 4.0, np.where(ph.in_generic_group, 0.6, 1.0))
    base *= np.where(ph.is_mitm, 1.5, 1.0)
    # expensive drugs sell fewer boxes; then scale to a realistic turnover in medicines
    # (large ~ 6,500 EUR/day ~ 2.4 MEUR/year, small ~ 2,600 EUR/day; public prices from the BDPM)
    price = ph.price.fillna(ph.price.median()).clip(lower=1).values
    base *= np.minimum(1.0, 15.0 / price) ** 1.2
    target = {"large": 6500.0, "small": 2600.0}[size]
    base *= target / float((base * price).sum())
    ph["daily_demand"] = base.clip(0.005, 60).round(4)
    ph["winter_class"] = ph.atc3.isin(WINTER_ATC)
    return ph.reset_index(drop=True)


def sales(ph: pd.DataFrame, start, end, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    days = pd.date_range(start, end, freq="D")
    doy = days.dayofyear.values
    seas_w = 1 + 0.45 * np.cos(2 * np.pi * (doy - 15) / 365)
    weekday = np.where(days.dayofweek.values == 6, 0.0, np.where(days.dayofweek.values == 5, 0.7, 1.12))
    base = ph.daily_demand.values
    lam = np.outer(weekday, base)
    w = ph.winter_class.values
    lam[:, w] = np.outer(seas_w * weekday, base[w])
    return pd.DataFrame(rng.poisson(lam), index=days, columns=ph.product_id)
