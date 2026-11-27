"""Step 4 - the decision rule (rung 1). The models are not trusted with quantities.

Guardrails are code, not captions: cap at 28 days of forecast demand, ANSM/wholesaler
quota, network freeze, and free text can never change a quantity (eval C17).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

NORMAL_COVER = 14
EXTRA_COVER = 28
BUY_THRESHOLD = 0.50
WATCH_THRESHOLD = 0.25


@dataclass
class Decision:
    decision: str
    buy_qty: int
    why: str
    cap: int | None = None
    flags: list[str] = field(default_factory=list)


def decide(stock: float, demand: float | None, history_days: int, risk: float,
           status: str = "none", quota: int | None = None, network_freeze: bool = False,
           buy_threshold: float = BUY_THRESHOLD, watch_threshold: float = WATCH_THRESHOLD,
           notice_text: str | None = None) -> Decision:
    flags = []
    if notice_text:
        flags.append("notice shown as text only - it cannot change the quantity")
    if network_freeze:
        return Decision("FROZEN", 0, "network freeze: too many pharmacies buying this product", flags=flags)
    if stock <= 0 and status == "shortage":
        return Decision("TOO LATE", 0, "stock already at zero and the lab is short", flags=flags)
    if history_days < 14 or demand is None:
        return Decision("WATCH", 0, "not enough sales history to forecast", flags=flags)
    if risk >= buy_threshold:
        cap = math.floor(demand * EXTRA_COVER)
        qty = math.ceil(demand * (NORMAL_COVER + EXTRA_COVER) - stock)
        qty = min(qty, cap) if quota is None else min(qty, cap, quota)
        if qty > 0:
            why = "quota" if quota is not None and qty == quota else ("cap" if qty == cap else "target cover")
            return Decision("BUY", int(qty), f"risk {risk:.0%}; quantity limited by {why}", cap=cap, flags=flags)
        return Decision("NO", 0, "high risk but enough stock", cap=cap, flags=flags)
    if risk >= watch_threshold:
        return Decision("WATCH", 0, "risk in the watch band", flags=flags)
    return Decision("NO", 0, "normal reorder", flags=flags)
