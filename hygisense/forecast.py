"""Step 2 - demand forecast -> days of stock left, with a range (rung 2).

Baseline: mean of the last 56 days. Model: mean of the last 28 days x a seasonal
index learnt from the same month last year (needs >= 365 days of history).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def naive(sales: pd.DataFrame, day: pd.Timestamp) -> pd.Series:
    return sales.loc[day - pd.Timedelta(days=55):day].mean()


def seasonal(sales: pd.DataFrame, day: pd.Timestamp) -> tuple[pd.Series, pd.Series]:
    """Return (daily demand forecast, daily std) for the next 2-4 weeks."""
    recent = sales.loc[day - pd.Timedelta(days=27):day]
    level = recent.mean()
    hist = sales.loc[:day]
    if len(hist) >= 400:
        ly = day - pd.Timedelta(days=365)
        last_year_recent = sales.loc[ly - pd.Timedelta(days=27):ly].mean()
        last_year_next = sales.loc[ly + pd.Timedelta(days=1):ly + pd.Timedelta(days=28)].mean()
        n = sales.loc[ly - pd.Timedelta(days=27):ly].sum()
        ratio = ((last_year_next + 0.05) / (last_year_recent + 0.05)).clip(0.6, 1.8)
        w = n / (n + 60)                      # shrink towards 1 when last year had few sales
        level = level * (w * ratio + (1 - w))
    std = recent.std().fillna(0)
    return level, std


def predict(sales: pd.DataFrame, day: pd.Timestamp) -> tuple[pd.Series, pd.Series]:
    """The forecast used by the product: the 56-day mean.

    The seasonal version did not beat it on the backtest (evals/report_v0.md), so by the
    course's ladder rule we keep the simpler one.
    """
    recent = sales.loc[day - pd.Timedelta(days=55):day]
    return recent.mean(), recent.std().fillna(0)


def days_left(stock: float, demand: float, std: float) -> tuple[float | None, float | None, float | None]:
    if demand <= 0:
        return None, None, None
    d = stock / demand
    hi_dem = demand + std / np.sqrt(7)
    lo_dem = max(demand - std / np.sqrt(7), demand * 0.3)
    return round(d, 1), round(stock / hi_dem, 1), round(stock / lo_dem, 1)
