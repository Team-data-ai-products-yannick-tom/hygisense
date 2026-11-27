"""Step 3b v2 - the vigilance index: how much riskier than average is this product, 8 weeks ahead.

Why not a big model: on the ANSM snapshot + FDA list, a logistic regression and gradient boosting
learned unstable signs (the history is short and biased), AUC 0.58-0.68 on 2026. A transparent
relative-risk score does better and can be explained to a pharmacist line by line:

    index = product of the relative risks of the flags it carries

Relative risks are measured on the VALIDATION year (2025) only, then the index is scored once on
2026 (test). Flags: drug of major therapeutic interest, only one lab makes it, already short in
the United States (FDA), nervous-system class, same substance already short in France.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FLAGS = {
    "is_mitm": "Intérêt thérapeutique majeur",
    "single_source": "Un seul labo en France",
    "us_any": "En pénurie aux États-Unis",
    "atc_N": "Système nerveux",
    "sub_on": "Même molécule en pénurie ailleurs",
}


def add_flags(f: pd.DataFrame) -> pd.DataFrame:
    f = f.copy()
    f["us_any"] = (f.get("us_short_active", 0) > 0).astype(int)
    f["sub_on"] = (f.substance_ongoing > 0).astype(int)
    return f


class VigilanceIndex:
    """Worked example (numbers measured on 2025):
        a drug of major therapeutic interest (x8.1) made by a single lab (x4.4)
        -> index = 8.1 x 4.4 = 35.6 (before normalisation): about 36 times the risk of an average drug.
        probability in 8 weeks = index x base rate (share of products declared in 8 weeks), capped at 90 %.
    """

    def fit(self, d: pd.DataFrame):
        """Learn one relative risk per flag. `d` has one row per (product, day) and y = 1 if the
        product was declared short in the next 8 weeks."""
        d = add_flags(d)
        self.base = float(d.y.mean())          # base rate: how often an average product gets declared
        self.rr = {}
        for c in FLAGS:
            on, off = d[d[c] > 0], d[d[c] == 0]             # products with / without the flag
            a = (on.y.sum() + 0.5) / (len(on) + 1)           # declaration rate WITH the flag
            b = (off.y.sum() + 0.5) / (len(off) + 1)         # declaration rate WITHOUT the flag
            # (+0.5 / +1 avoid dividing by zero when a flag is rare)
            self.rr[c] = float(a / b)                        # relative risk: "x times more often"
        # mean index on the fitting data, so that index = 1 means "average product"
        self.norm = float(self._raw(d).mean())
        return self

    def _raw(self, f):
        """Multiply the relative risks of the flags each product carries (1 if it carries none)."""
        s = np.ones(len(f))
        for c, r in self.rr.items():
            s = s * np.where(f[c] > 0, r, 1.0)
        return s

    def index(self, f: pd.DataFrame) -> np.ndarray:
        """Index 1 = average product; 10 = ten times the average risk."""
        return self._raw(add_flags(f)) / self.norm

    def predict(self, f: pd.DataFrame) -> np.ndarray:
        """Probability of a declaration within 8 weeks (index x average rate, capped)."""
        return np.clip(self.index(f) * self.base, 0, 0.9)

    def reasons(self, row) -> list[str]:
        """The flags behind the index, strongest first: what the app shows under "Pourquoi ce risque"."""
        row = add_flags(pd.DataFrame([row])).iloc[0]
        on = sorted([c for c in FLAGS if row[c] > 0], key=lambda c: -self.rr[c])
        return [f"{FLAGS[c]} (risque ×{self.rr[c]:.1f})".replace(".", ",") for c in on]

    def card(self) -> dict:
        return {"base_rate_8w": round(self.base, 5), "relative_risks": {c: round(r, 2) for c, r in self.rr.items()}}
