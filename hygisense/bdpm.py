"""Load the official files of the Base de données publique des médicaments (BDPM).

Source: https://base-donnees-publique.medicaments.gouv.fr/telechargement (ANSM, HAS, UNCAM),
Licence Ouverte. Files are tab-separated, no header, Windows-1252 except the presentations file.
Put them in data/ as downloaded (bdpm_<NAME>.txt or <NAME>.txt).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

COLS = {
    "CIS_bdpm": ["cis", "name", "form", "route", "amm_status", "procedure", "marketing",
                 "amm_date", "bdm_status", "eu_number", "holder", "enhanced_surveillance"],
    "CIS_CIP_bdpm": ["cis", "cip7", "pack", "pack_status", "pack_marketing", "pack_date", "cip13",
                     "hospital_approval", "reimb_rate", "price_ex", "price", "fee", "reimb_text"],
    "CIS_GENER_bdpm": ["group_id", "group_label", "cis", "generic_type", "order"],
    "CIS_CIP_Dispo_Spec": ["cis", "cip13", "code", "status", "start", "updated", "back_on", "ansm_link"],
    "CIS_MITM": ["cis", "atc", "name", "holder", "operator", "mitm_date", "link"],
    "CIS_COMPO_bdpm": ["cis", "element", "substance_code", "substance", "dose", "dose_ref", "nature", "link_no"],
}


def _path(name: str) -> Path:
    for p in (DATA / f"bdpm_{name}.txt", DATA / f"{name}.txt"):
        if p.exists():
            return p
    raise FileNotFoundError(f"{name}.txt not found in {DATA} - download it from the BDPM (see data/README.md)")


def read(name: str) -> pd.DataFrame:
    raw = _path(name).read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
    rows = [line.split("\t") for line in text.splitlines() if line.strip()]
    n = len(COLS[name])
    rows = [(r + [""] * n)[:n] for r in rows]
    df = pd.DataFrame(rows, columns=COLS[name])
    return df.apply(lambda s: s.str.strip())


def load() -> dict[str, pd.DataFrame]:
    d = {k: read(k) for k in COLS}
    for k in ("start", "updated", "back_on"):
        d["CIS_CIP_Dispo_Spec"][k] = pd.to_datetime(d["CIS_CIP_Dispo_Spec"][k], format="%d/%m/%Y", errors="coerce")
    d["CIS_bdpm"]["amm_date"] = pd.to_datetime(d["CIS_bdpm"]["amm_date"], format="%d/%m/%Y", errors="coerce")
    p = d["CIS_CIP_bdpm"]
    p["price"] = pd.to_numeric(p.price.str.replace(".", "", regex=False).str.replace(",", "."), errors="coerce")
    p["reimb_rate"] = pd.to_numeric(p.reimb_rate.str.replace("%", "").str.strip(), errors="coerce")
    return d


def shortage_events(d: dict, snapshot: pd.Timestamp) -> pd.DataFrame:
    """ANSM supply problems as events: one row per CIS and start date.

    code 1 = rupture (stock-out at the lab), 2 = tension (reduced supply).
    code 3 (discontinuation) is not a shortage; code 4 (back in stock) only gives an end date,
    its start is not published - those CIS are returned separately to be left out of the negatives.
    """
    s = d["CIS_CIP_Dispo_Spec"]
    ev = s[s.code.isin(["1", "2"]) & s.start.notna()].copy()
    ev["end"] = ev.back_on.fillna(snapshot + pd.Timedelta(days=60))  # still ongoing at the snapshot
    ev["status"] = ev.code.map({"1": "rupture", "2": "tension"})
    ev = (ev.sort_values("code").drop_duplicates(["cis", "start"])
            [["cis", "status", "start", "end", "ansm_link"]].rename(columns={"cis": "product_id"}))
    unknown_start = set(s[s.code == "4"].cis) - set(ev.product_id)
    return ev.sort_values(["product_id", "start"]).reset_index(drop=True), unknown_start
