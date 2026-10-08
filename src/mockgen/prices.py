"""Deterministic list prices per firm, service and year (anchored on the 2024 group harmonisation workbook HO-006)."""
from __future__ import annotations

# 2024 list price in GBP, unit
BASE = {
    "synthesis": [("Analogue preparation", 950, "per compound"), ("Route scout and delivery", 14500, "per route")],
    "herg": 185, "cyp_inhib": 110, "cyp_ic50": 240, "kinase_primary": 160, "kinase_panel": (1450, "per compound (panel)"),
    "mic_stab": 140, "hep_stab": 220, "ppb": 165, "caco2": 260, "solubility": 60,
    "rodent_pk": (3800, "per compound (single route, 3 animals)"), "comp_screen": (9500, "per target campaign"),
    "bioinf": (12500, "per dataset"), "stability": (950, "per pull (all tests, one condition)"),
    "method_val": (18500, "per method"), "form_screen": (6800, "per vehicle ladder"),
}
# US firms quote in USD; anchors from HO-006
USD = {"herg": 290, "cyp_inhib": 165, "mic_stab": (330, "per compound (2 species)"), "ppb": 260}
USD_FACTOR = 1.55
DRIFT = 1.035  # list prices rise about 3.5% a year


def _round(x: float) -> int:
    step = 50 if x >= 1000 else 5
    return int(round(x / step) * step)


def list_prices(w, firm_letter: str, year: int) -> list[list]:
    f = w.firms[firm_letter]
    us = f.location.country.upper() in ("US", "USA", "UNITED STATES")
    cur = "USD" if us else "GBP"
    k = DRIFT ** (year - 2024)
    rows = []
    for a in w.assays.values():
        names = [x if isinstance(x, str) else x.get("name") for x in ((a.get("variants") or {}).get(firm_letter) or [])]
        if not names:
            continue
        base = BASE.get(a["id"])
        if base is None:
            continue
        items = base if isinstance(base, list) else [(n, *(base if isinstance(base, tuple) else (base, "per compound"))) for n in names[:1]]
        for name, price, unit in items:
            if us:
                anc = USD.get(a["id"])
                if anc is not None:
                    price, unit = anc if isinstance(anc, tuple) else (anc, unit)
                else:
                    price = price * USD_FACTOR
            band = "5% >30 cpds; 10% >80 cpds" if unit.startswith("per compound") else "none"
            rows.append([name, unit, _round(price * k), cur, band])
    return rows
