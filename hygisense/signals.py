"""External early-warning signals: US shortages (FDA) and French epidemics (Réseau Sentinelles).

- FDA drug shortages (openFDA, 1,585 records since 2012): a substance short in the US is often
  short in Europe a few weeks later (same active-ingredient factories).
- Réseau Sentinelles (Inserm / Sorbonne Université), weekly incidence per 100,000:
  influenza-like illness (grippe), acute respiratory infections (ira), acute diarrhoea.
  Epidemics push up demand for antibiotics, respiratory drugs and paracetamol.
"""
from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

from .bdpm import DATA

SALTS = {"HYDROCHLORIDE", "SODIUM", "SULFATE", "POTASSIUM", "CALCIUM", "MESYLATE", "MALEATE", "TARTRATE",
         "CITRATE", "ACETATE", "PHOSPHATE", "BESYLATE", "FUMARATE", "SUCCINATE", "HYDROBROMIDE", "MAGNESIUM",
         "DIHYDRATE", "MONOHYDRATE", "TRIHYDRATE", "ANHYDROUS", "DIMESYLATE", "BROMIDE", "CHLORIDE", "HYCLATE",
         "CHLORHYDRATE", "SULFATE", "MALEATE", "TARTRATE", "ACETATE", "BESILATE", "FUMARATE", "SUCCINATE",
         "BROMHYDRATE", "MESILATE", "DE", "D", "HEMIHYDRATE", "SODIQUE", "POTASSIQUE", "CALCIQUE", "BASE",
         "ACIDE", "ACID", "LYSINE", "RESINATE", "IODURE", "IODIDE", "OXYDE", "OXIDE"}


def stem(name: str) -> str:
    """'CHLORHYDRATE DE METFORMINE' -> 'METFOR' ; 'METFORMIN HYDROCHLORIDE' -> 'METFOR'."""
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().upper()
    words = [w for w in re.split(r"[^A-Z]+", s) if w and w not in SALTS and len(w) > 2]
    return words[0][:6] if words else ""


# ---------------------------------------------------------------- FDA
def load_fda(snapshot: pd.Timestamp) -> pd.DataFrame:
    files = sorted(DATA.glob("hyg_fda_shortages_*.csv"))
    if not files:
        raise FileNotFoundError("hyg_fda_shortages_*.csv not found in data/ (see data/README.md)")
    f = pd.concat([pd.read_csv(p) for p in files], ignore_index=True)
    f["start"] = pd.to_datetime(f.initial_posting_date, errors="coerce")
    upd = pd.to_datetime(f.update_date, errors="coerce")
    # resolved: end ~ last update; current / to be discontinued: still running at the snapshot
    f["end"] = np.where(f.status == "Resolved", upd, snapshot + pd.Timedelta(days=60))
    f["end"] = pd.to_datetime(f["end"])
    subs = f.substances.fillna("").str.split("|")
    fallback = f.generic_name.fillna("").str.split(r",| Tablet| Capsule| Injection| Oral| Solution").str[0]
    f["stem"] = [stem(s[0]) if s and s[0] else stem(g) for s, g in zip(subs, fallback)]
    return f[f.start.notna() & (f.stem != "")][["stem", "generic_name", "start", "end", "status",
                                                  "shortage_reason"]].reset_index(drop=True)


# ---------------------------------------------------------------- Sentinelles
def load_epidemics() -> pd.DataFrame:
    p = DATA / "hyg_sentinelles.csv"
    e = pd.read_csv(p)
    e["date"] = [pd.Timestamp.fromisocalendar(int(str(w)[:4]), min(int(str(w)[4:]), 52), 1) for w in e.week]
    return e.pivot_table(index="date", columns="indicator", values="inc100").sort_index()


class EpidemicModel:
    """Forecast the incidence 4 weeks ahead (weekly, per 100,000).

    Baselines: persistence (same as this week) and climatology (median of the same week in past years).
    Model: log-linear blend of the current level, its 2-week trend and the climatology, fitted by
    least squares on past seasons only.
    """
    H = 4

    def __init__(self, series: pd.Series):
        self.s = series.dropna()
        self.coef = None

    def _clim(self, date, upto):
        hist = self.s[self.s.index < upto]
        wk = (date + pd.Timedelta(weeks=self.H)).isocalendar().week
        same = hist[[d.isocalendar().week == wk for d in hist.index]]
        return float(same.tail(10).median()) if len(same) else float(hist.median())

    def _x(self, date, upto):
        """The 4 inputs of the forecast for one week: constant, today's level, its 2-week trend,
        and the usual level for that time of year (median of the same week in past years).
        Logs (log1p) so that a doubling counts the same at 50 or at 500 cases."""
        s = self.s[self.s.index <= date]
        now = s.iloc[-1]
        prev = s.iloc[-3] if len(s) >= 3 else now
        return np.array([1.0, np.log1p(now), np.log1p(now) - np.log1p(prev), np.log1p(self._clim(date, upto))])

    def fit(self, upto: pd.Timestamp):
        """Least squares on past weeks only (before `upto`): for every week, inputs today -> level 4 weeks later."""
        X, y = [], []
        dates = self.s.index[(self.s.index < upto - pd.Timedelta(weeks=self.H))]
        for d in dates[10:]:
            target = self.s.get(d + pd.Timedelta(weeks=self.H))
            if target is None or np.isnan(target):
                continue
            X.append(self._x(d, d))
            y.append(np.log1p(target))
        self.coef, *_ = np.linalg.lstsq(np.array(X), np.array(y), rcond=None)
        return self

    def predict(self, date):
        """Incidence expected 4 weeks after `date` (cases per 100,000)."""
        return float(np.expm1(self._x(date, date) @ self.coef))

    def evaluate(self, start, end) -> dict:
        err = {"persistence": [], "climatology": [], "model": []}
        for d in self.s.index[(self.s.index >= start) & (self.s.index <= end - pd.Timedelta(weeks=self.H))]:
            truth = self.s.get(d + pd.Timedelta(weeks=self.H))
            if truth is None or np.isnan(truth):
                continue
            err["persistence"].append(abs(self.s[d] - truth))
            err["climatology"].append(abs(self._clim(d, d) - truth))
            err["model"].append(abs(self.predict(d) - truth))
        return {k: round(float(np.mean(v)), 1) for k, v in err.items()}


# ---- regional Sentinelles series (one file per indicator, geo=REG, downloaded from the sentiweb API)
REG_INDICATORS = {3: "grippe", 25: "ira", 6: "diarrhee"}


def load_regional() -> pd.DataFrame | None:
    """Long table: date, indicator, region (INSEE code, old 22 regions), name, inc100. None if no file."""
    frames = []
    for p in sorted(DATA.glob("hyg_sentinelles_reg_*.csv")):
        e = pd.read_csv(p, comment="#")
        e = e[e.indicator.isin(REG_INDICATORS)].copy()
        e["inc100"] = pd.to_numeric(e.inc100, errors="coerce")   # some weeks have no estimate
        e["indicator"] = e.indicator.map(REG_INDICATORS)
        frames.append(e[["week", "indicator", "geo_insee", "geo_name", "inc100"]])
    if not frames:
        return None
    e = pd.concat(frames, ignore_index=True)
    e["date"] = [pd.Timestamp.fromisocalendar(int(str(w)[:4]), min(int(str(w)[4:]), 52), 1) for w in e.week]
    e = e.rename(columns={"geo_insee": "region", "geo_name": "name"})
    e["name"] = e.name.str.replace("-", " ").str.title()
    return e.drop(columns="week")


def regional_series(reg: pd.DataFrame, region: int) -> pd.DataFrame:
    r = reg[(reg.region == region) & (reg.date >= "2009-01-01")]   # same window as the national fit
    return r.pivot_table(index="date", columns="indicator", values="inc100", aggfunc="mean").sort_index()
