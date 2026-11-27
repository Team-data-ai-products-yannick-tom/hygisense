"""Step 3 - risk that the lab declares a shortage (tension or rupture) in the next 8 weeks.

Classical ML (logistic regression), trained on the REAL ANSM declarations published in the
BDPM availability file. Features only use what is public and known on the day:
the catalogue (how many labs make the same substance, generic group, MITM, form...) and
the declarations that started BEFORE the day (same substance, same lab, same product).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HORIZON = 56
ATC1 = ["A", "B", "C", "J", "N", "R", "L", "?"]
FEATURES = ["log_holders_substance", "single_source", "log_in_group", "is_generic", "is_mitm", "oral",
            "log_holder_size", "age_decades", "log_price", "winter", "winter_x_class",
            "own_past_2y", "substance_ongoing", "substance_recent_90d", "group_ongoing", "holder_recent_365d"] \
           + [f"atc_{a}" for a in ATC1]

REASON_TEXT = {
    "substance_ongoing": "same substance already in shortage at another lab",
    "substance_recent_90d": "same substance declared short in the last 90 days",
    "group_ongoing": "a generic of the same group is short",
    "holder_recent_365d": "this lab declared other shortages this year",
    "own_past_2y": "already short in the last 2 years",
    "single_source": "only one lab makes it",
    "log_holders_substance": "few labs make this substance",
    "is_mitm": "drug of major therapeutic interest",
    "winter_x_class": "winter peak for this class",
    "is_generic": "generic",
    "us_short_active": "same substance currently short in the United States (FDA)",
    "us_short_new_180d": "same substance declared short in the United States in the last 6 months (FDA)",
    "epi_x_class": "epidemic forecast high for the next 4 weeks (Sentinelles)",
}
FEATURES_BASE = list(FEATURES)
FEATURES_EXT = FEATURES_BASE + ["us_short_active", "us_short_new_180d", "epi_x_class"]


def static_features(prod: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame({"product_id": prod.product_id})
    f["log_holders_substance"] = np.log(prod.n_holders_substance.fillna(1).clip(1))
    f["single_source"] = (prod.n_holders_substance.fillna(1) <= 1).astype(int)
    f["log_in_group"] = np.log(prod.n_in_group.clip(1))
    f["is_generic"] = prod.is_generic.astype(int)
    f["is_mitm"] = prod.is_mitm.astype(int)
    f["oral"] = prod.oral.astype(int)
    f["log_holder_size"] = np.log(prod.holder_size.clip(1))
    f["age_decades"] = prod.age_years.fillna(prod.age_years.median()) / 10
    f["log_price"] = np.log1p(prod.price.fillna(prod.price.median()))
    f["winter_class"] = prod.atc3.isin(("J01", "R03", "R05", "R01", "R06", "J05")).astype(int)
    for a in ATC1:
        f[f"atc_{a}"] = (prod.atc1 == a).astype(int) if a != "?" else (~prod.atc1.isin(ATC1[:-1])).astype(int)
    f["substance_code"] = prod.substance_code.values
    f["group_id"] = prod.group_id.values
    f["holder"] = prod.holder.values
    from .signals import stem
    f["stem"] = prod.substance.fillna("").map(stem).values
    f["resp_class"] = prod.atc3.isin(("J01", "R03", "R05", "R01", "R06", "J05", "N02")).astype(int).values
    return f.reset_index(drop=True)


def annotate_events(ev: pd.DataFrame, sf_all: pd.DataFrame) -> pd.DataFrame:
    """Attach substance, generic group and lab to each event (from the FULL catalogue)."""
    return ev.merge(sf_all[["product_id", "substance_code", "group_id", "holder"]], on="product_id", how="inner")


EXT = {}   # {"fda": DataFrame, "epi": Series of 4-week incidence forecasts} - set by set_external()


def set_external(fda: pd.DataFrame, epi_forecast: pd.Series):
    EXT["fda"], EXT["epi"] = fda, epi_forecast


def features_on(day: pd.Timestamp, sf: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    f = sf.copy()
    f["day"] = day
    f["winter"] = int(day.month in (11, 12, 1, 2))
    f["winter_x_class"] = f.winter * f.winter_class
    known = ev[ev.start <= day]
    ongoing = known[known.end > day]
    f["in_event_now"] = f.product_id.isin(ongoing.product_id)
    past2 = known[known.start > day - pd.Timedelta(days=730)].groupby("product_id").size()
    f["own_past_2y"] = f.product_id.map(past2).fillna(0).clip(0, 3)

    def other(col, sub, cap=5):
        cnt = sub.groupby(col).size()
        own = sub.groupby("product_id").size()
        v = f[col].map(cnt).fillna(0) - f.product_id.map(own).fillna(0)
        return np.log1p(v.clip(0, cap))

    f["substance_ongoing"] = other("substance_code", ongoing)
    f["substance_recent_90d"] = other("substance_code", known[known.start > day - pd.Timedelta(days=90)])
    f["group_ongoing"] = other("group_id", ongoing)
    f["holder_recent_365d"] = other("holder", known[known.start > day - pd.Timedelta(days=365)], cap=20)
    if EXT:
        fda = EXT["fda"]
        act = fda[(fda.start <= day) & (fda.end > day)].groupby("stem").size()
        new = fda[(fda.start <= day) & (fda.start > day - pd.Timedelta(days=180))].groupby("stem").size()
        f["us_short_active"] = np.log1p(f.stem.map(act).fillna(0).clip(0, 5))
        f["us_short_new_180d"] = np.log1p(f.stem.map(new).fillna(0).clip(0, 5))
        epi = EXT["epi"]
        val = float(epi[epi.index <= day].iloc[-1]) if (epi.index <= day).any() else 0.0
        f["epi_forecast"] = np.log1p(val)
        f["epi_x_class"] = f.epi_forecast * f.resp_class
    return f


def build_dataset(sf, ev, start, end, step_days=28, exclude=()) -> pd.DataFrame:
    frames = []
    for day in pd.date_range(start, end, freq=f"{step_days}D"):
        f = features_on(day, sf, ev)
        f = f[~f.in_event_now & ~f.product_id.isin(exclude)]
        nxt = ev[(ev.start > day) & (ev.start <= day + pd.Timedelta(days=HORIZON))].product_id
        f["y"] = f.product_id.isin(nxt).astype(int)
        frames.append(f)
    return pd.concat(frames, ignore_index=True)


class RiskModel:
    def __init__(self, features=None):
        self.features = list(features or FEATURES)
        self.m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, C=0.3))

    def fit(self, d):
        self.m.fit(d[self.features], d.y)
        return self

    def predict(self, f):
        return self.m.predict_proba(f[self.features])[:, 1]

    def coefficients(self) -> pd.Series:
        lr = self.m[-1]
        return pd.Series(lr.coef_[0], index=self.features).sort_values()

    def reasons(self, row, k=3):
        sc, lr = self.m[0], self.m[-1]
        z = (row[self.features].astype(float).values - sc.mean_) / sc.scale_
        contrib = pd.Series(lr.coef_[0] * z, index=self.features)
        top = [c for c in contrib.sort_values(ascending=False).index if contrib[c] > 0.15 and c in REASON_TEXT][:k]
        return [REASON_TEXT[c] for c in top] or ["no strong signal"]
