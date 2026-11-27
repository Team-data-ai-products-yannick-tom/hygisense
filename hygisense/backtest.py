"""Backtest on one simulated pharmacy, with the REAL ANSM declarations.

Replay every day of the test window: "would Hygisense have said BUY while the product was still
fully orderable, at least 7 days before this pharmacy's shelf would have been empty?"

Do-nothing world: the pharmacy keeps ~14 days of cover with its normal reorder (order up to 14 days
when below 7, delivered next day). During an ANSM 'tension' the wholesaler fills 40 % of the order;
during a 'rupture', nothing. A declaration counts in the denominator only if it would have
emptied this pharmacy's shelf.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import forecast
from .decide import EXTRA_COVER, NORMAL_COVER, decide
from .risk import features_on

FILL = {"tension": 0.4, "rupture": 0.0}
DECLARED_RISK = 0.95   # rung 1: an ANSM declaration on this exact product is not a guess


def fill_matrix(days, ids, ev, buffer_days) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Share of an order the wholesaler delivers, and 'declared and still orderable' flags.

    Wholesalers must hold at least 2 weeks of their customers' consumption (art. R5124-59 CSP;
    18.5 days on average, IGAS 2014): after a declaration they keep delivering for `buffer_days`.
    """
    m = pd.DataFrame(1.0, index=days, columns=ids)
    declared = pd.DataFrame(False, index=days, columns=ids)
    for e in ev[ev.product_id.isin(ids)].itertuples():
        cut = e.start + pd.Timedelta(days=buffer_days)
        declared.loc[(declared.index >= e.start) & (declared.index < cut), e.product_id] = True
        mask = (m.index >= cut) & (m.index < e.end)
        m.loc[mask, e.product_id] = np.minimum(m.loc[mask, e.product_id], FILL[e.status])
    return m, declared


def simulate_stock(sales, fill, days, demand, buys=None):
    """Normal reorder: below 7 days (and never below 1 box) -> order up to 14 days (at least 2 boxes).
    Boxes missing at the counter are counted only on days the wholesaler is short (fill < 1)."""
    target = np.maximum(np.ceil(demand * NORMAL_COVER), 2)
    point = np.maximum(demand * 7, 1)
    stock = target.copy()
    path, lost = {}, {}
    pending = pd.Series(0.0, index=stock.index)
    for d in days:
        stock = stock + pending
        pending[:] = 0
        s = sales.loc[d]
        sold = np.minimum(stock, s)
        lost[d] = (s - sold) * (fill.loc[d] < 1)
        stock = stock - sold
        path[d] = stock.copy()
        low = stock < point
        reorder = (target - stock).clip(lower=0)
        pending[low] += (reorder[low] * fill.loc[d][low]).round()
        if buys and d in buys:
            for pid, q in buys[d].items():
                if fill.at[d, pid] == 1.0:
                    pending[pid] += q
    return pd.DataFrame(path).T, pd.DataFrame(lost).T


def run(ph, sales, sf, ev, model, start, end, buy_threshold, watch_threshold, buffer_days=14):
    days = pd.date_range(start, end, freq="D")
    ids = list(ph.product_id)
    demand = ph.set_index("product_id").daily_demand
    fill, declared = fill_matrix(days, ids, ev, buffer_days)
    stock_path, lost_nothing = simulate_stock(sales, fill, days, demand)

    risk, dem = {}, {}
    sfp = sf[sf.product_id.isin(ids)].reset_index(drop=True)
    for d in days:
        f = features_on(d, sfp, ev)
        risk[d] = pd.Series(model.predict(f), index=f.product_id.values)
        dem[d], _ = forecast.predict(sales, d)
    model_risk = pd.DataFrame(risk).T[ids]
    risk = model_risk.where(~declared, np.maximum(model_risk, DECLARED_RISK))
    dem = pd.DataFrame(dem).T[ids]

    recs = []
    hot = risk.stack()
    hot = hot[hot >= buy_threshold]
    for (d, pid), r in hot.items():
        if fill.at[d, pid] < 1.0:      # the wholesaler can no longer deliver: too late to buy ahead
            continue
        st = stock_path.at[d, pid]
        dec = decide(st, float(dem.at[d, pid]), 365, float(r),
                     "shortage" if fill.at[d, pid] == 0 else "none",
                     buy_threshold=buy_threshold, watch_threshold=watch_threshold)
        if dec.decision == "BUY":
            recs.append((d, pid, dec.buy_qty, st, float(dem.at[d, pid]), float(r)))
    recs = pd.DataFrame(recs, columns=["day", "product_id", "qty", "stock", "demand", "risk"])

    evw = ev[ev.product_id.isin(ids) & (ev.start >= start) & (ev.start <= end)]
    rows = []
    for e in evw.itertuples():
        col = stock_path[e.product_id]
        short_days = fill[e.product_id] < 1
        empty = col[(col.index >= e.start) & (col.index < e.end) & (col <= 0) & short_days]
        if empty.empty:
            continue
        so = empty.index[0]
        cut = e.start + pd.Timedelta(days=buffer_days)
        r = recs[(recs.product_id == e.product_id) & (recs.day < cut)
                 & (recs.day >= e.start - pd.Timedelta(days=56)) & (recs.day <= so - pd.Timedelta(days=7))]
        rows.append({"product_id": e.product_id, "status": e.status, "start": e.start,
                     "stockout_do_nothing": so, "anticipated": not r.empty,
                     "first_buy": r.day.min() if not r.empty else pd.NaT,
                     "before_declaration": bool((r.day < e.start).any()), "ansm_link": e.ansm_link})
    events = pd.DataFrame(rows, columns=["product_id", "status", "start", "stockout_do_nothing",
                                         "anticipated", "first_buy", "before_declaration", "ansm_link"])

    useless = episodes = 0
    follow = {}
    for pid, g in recs.sort_values("day").groupby("product_id"):
        last = None
        for row in g.itertuples():
            if last is not None and (row.day - last).days <= 28:
                continue
            last = row.day
            episodes += 1
            follow.setdefault(row.day, {})[pid] = row.qty
            # useless = the shelf would not have emptied in the 8 weeks anyway
            col = stock_path[pid]
            window = col[(col.index > row.day) & (col.index <= row.day + pd.Timedelta(days=56))]
            useless += int((window > 0).all())
    cap_breaches = int((recs.qty > np.floor(recs.demand * EXTRA_COVER)).sum()) if len(recs) else 0
    _, lost_with = simulate_stock(sales, fill, days, demand, buys=follow)
    # boxes missing at the counter in the 12 weeks after each declaration of the window
    win_nothing = win_with = 0.0
    for e in evw.itertuples():
        sl = slice(e.start, e.start + pd.Timedelta(days=84))
        win_nothing += float(lost_nothing.loc[sl, e.product_id].sum())
        win_with += float(lost_with.loc[sl, e.product_id].sum())
    return {"events": events, "recs": recs, "episodes": episodes, "useless": useless,
            "cap_breaches": cap_breaches, "lost_units_do_nothing": win_nothing,
            "lost_units_with": win_with, "risk": risk, "model_risk": model_risk, "declared": declared, "dem": dem,
            "stock_path": stock_path, "fill": fill}
