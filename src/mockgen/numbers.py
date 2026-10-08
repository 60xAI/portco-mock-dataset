"""Deterministic assay numbers for every project (no LLM).

Output: numbers/compounds.json (all enumerated series compounds) and numbers/<PRJ>.json per project:
  tables: {key: {title, columns, rows, notes}}   rendered verbatim into workbooks/reports via table_ref
  values: {key: display string}                  referenced from text as {{PRJxxxx:key}}
"""
from __future__ import annotations

import json
import math
import random
import zlib
from datetime import timedelta

import numpy as np

from . import admet, chem
from .paths import NUMBERS, SEED
from .world import load_world

CYPS = ["CYP1A2", "CYP2C9", "CYP2C19", "CYP2D6", "CYP3A4"]
CYP_KEYS = {"CYP1A2": "cyp1a2", "CYP2C9": "cyp2c9", "CYP2C19": "cyp2c19", "CYP2D6": "cyp2d6", "CYP3A4": "cyp3a4"}
CYP_CONTROLS = {"CYP1A2": ("furafylline", 1.8), "CYP2C9": ("sulfaphenazole", 0.35), "CYP2C19": ("ticlopidine", 1.2),
                "CYP2D6": ("quinidine", 0.06), "CYP3A4": ("ketoconazole", 0.03)}


def rng_for(*parts) -> random.Random:
    return random.Random(zlib.crc32(("|".join(map(str, (SEED,) + parts))).encode()))


def sig(x: float, n: int = 3) -> str:
    if x == 0 or not math.isfinite(x):
        return "0"
    d = n - int(math.floor(math.log10(abs(x)))) - 1
    d = max(0, d)
    return f"{round(x, d):.{d}f}"


def compound_id(series, idx: int) -> str:
    base = 1000 + (zlib.crc32(series.id.encode()) % 80) * 100
    return f"{series.compound_prefix}-{base + idx * 3 + (idx % 2):05d}"


def series_compounds(series) -> list[dict]:
    cs = chem.enumerate_series(series)
    out = []
    for i, c in enumerate(cs):
        d = dict(c)
        d["id"] = compound_id(series, i)
        d["series"] = series.id
        out.append(d)
    return out


def _frag_effect(series, smiles: str, scale: float) -> float:
    """Deterministic SAR offset per compound (sum of hashed R-group contributions)."""
    r = rng_for("sar", series.id, smiles)
    return r.gauss(0, scale)


class Ctx:
    def __init__(self, project, series, cmpds):
        self.p = project
        self.s = series
        self.c = cmpds
        self.smiles = [c["smiles"] for c in cmpds]
        self.tables = {}
        self.values = {}
        self._pred = {}

    def pred(self, key):
        if key not in self._pred:
            self._pred[key] = admet.predict(key, self.smiles) if self.smiles else None
        return self._pred[key]


def _herg(ctx: Ctx, top=30.0):
    r = rng_for(ctx.p.id, "herg")
    p = ctx.pred("herg")
    rows, ic50s = [], []
    for i, c in enumerate(ctx.c):
        pb = p[i] if p is not None else 0.4
        piC = 4.25 + 2.1 * pb + 0.22 * (c["clogp"] - 3) + 0.25 * min(c["basic_n"], 1) + _frag_effect(ctx.s, c["smiles"], 0.25)
        reps = []
        for k in range(2 if r.random() > 0.15 else 3):
            reps.append(10 ** (6 - (piC + r.gauss(0, 0.12))) )
        reps_um = [x for x in reps]
        gm = 10 ** np.mean([math.log10(x) for x in reps_um])
        flag = ""
        if r.random() < 0.04:
            flag = r.choice(["Seal resistance <500 MΩ in 1 of 3 cells; n=2 reported", "Precipitation observed at top concentration",
                             "Run 2 rejected (E-4031 outside range); repeated"])
        if gm >= top:
            disp, qual = f">{top:g}", ">"
            rep_disp = [f">{top:g}" if x >= top else sig(x, 2) for x in reps_um]
        else:
            disp, qual = sig(gm, 2), "="
            rep_disp = [sig(x, 2) if x < top else f">{top:g}" for x in reps_um]
        ic50s.append((gm, qual))
        pct10 = 100 / (1 + (gm / 10) ** 1.0) + r.gauss(0, 4)
        rows.append([c["id"], rep_disp[0], rep_disp[1], rep_disp[2] if len(rep_disp) > 2 else "", disp,
                     f"{max(-5, min(100, pct10)):.0f}", len(reps), flag])
    ctrl = 10 ** (6 - r.gauss(7.85, 0.08)) * 1000  # nM
    ctx.tables["herg"] = {"title": "hERG IC50 (automated patch clamp)", "columns": ["Compound", "IC50 rep 1 (µM)", "IC50 rep 2 (µM)", "IC50 rep 3 (µM)", "IC50 mean (µM)", "% inhibition @10 µM", "n", "QC note"],
                          "rows": rows, "notes": [f"Top concentration {top:g} µM; 6-point, 3-fold dilution; positive control E-4031 IC50 {sig(ctrl, 2)} nM (acceptance 5-50 nM)"]}
    vals = [g for g, q in ic50s]
    ctx.values.update({
        "herg.n_tested": str(len(rows)),
        "herg.n_lt_1uM": str(sum(1 for g, q in ic50s if q == "=" and g < 1)),
        "herg.n_1_10uM": str(sum(1 for g, q in ic50s if q == "=" and 1 <= g < 10)),
        "herg.n_ge_10uM": str(sum(1 for g, q in ic50s if q == ">" or g >= 10)),
        "herg.median_ic50_uM": (f">{top:g}" if np.median(vals) >= top else sig(float(np.median(vals)), 2)),
        "herg.control_e4031_nM": sig(ctrl, 2),
        "herg.top_conc_uM": f"{top:g}",
    })
    for i, (row) in enumerate(rows):
        ctx.values[f"herg.{row[0]}.ic50_uM"] = row[4]


def _cyp(ctx: Ctx):
    r = rng_for(ctx.p.id, "cyp")
    rows = []
    counts = {k: 0 for k in CYPS}
    for i, c in enumerate(ctx.c):
        row = [c["id"]]
        for iso in CYPS:
            p = ctx.pred(CYP_KEYS[iso])
            pb = p[i] if p is not None else 0.3
            pic = 4.1 + 2.0 * pb + 0.15 * (c["clogp"] - 3) + _frag_effect(ctx.s, c["smiles"] + iso, 0.3)
            ic = 10 ** (6 - pic)
            pct = 100 / (1 + ic / 10) + r.gauss(0, 5)
            pct = max(-12, min(100, pct))
            if pct > 50:
                counts[iso] += 1
            row.append(f"{pct:.0f}")
        rows.append(row)
    ctrls = {iso: sig(v * math.exp(r.gauss(0, 0.15)), 2) for iso, (n, v) in CYP_CONTROLS.items()}
    ctx.tables["cyp_inhib"] = {"title": "CYP inhibition, % inhibition at 10 µM (human liver microsomes, probe substrates)",
                               "columns": ["Compound"] + [f"{i} (%)" for i in CYPS], "rows": rows,
                               "notes": ["Single concentration 10 µM, duplicate incubations, mean reported; negative values = no inhibition",
                                         "Controls (IC50, µM): " + "; ".join(f"{CYP_CONTROLS[i][0]} ({i}) {ctrls[i]}" for i in CYPS)]}
    for iso in CYPS:
        ctx.values[f"cyp.n_gt50_{iso}"] = str(counts[iso])
        ctx.values[f"cyp.control_{iso}_uM"] = ctrls[iso]
    ctx.values["cyp.n_any_gt50"] = str(sum(1 for row in rows if any(float(x) > 50 for x in row[1:])))
    for row in rows:
        ctx.values[f"cyp.{row[0]}.CYP3A4_pct"] = row[5]


def _cyp_ic50(ctx: Ctx):
    r = rng_for(ctx.p.id, "cyp_ic50")
    p = ctx.pred("cyp3a4")
    rows = []
    for i, c in enumerate(ctx.c):
        pb = p[i] if p is not None else 0.3
        pic = 4.1 + 2.0 * pb + 0.15 * (c["clogp"] - 3) + _frag_effect(ctx.s, c["smiles"] + "CYP3A4", 0.3)
        ic = 10 ** (6 - pic) * math.exp(r.gauss(0, 0.2))
        rows.append([c["id"], ">50" if ic > 50 else sig(ic, 2), "midazolam" if r.random() < 0.6 else "testosterone"])
    ctx.tables["cyp_ic50"] = {"title": "CYP3A4 IC50 (µM)", "columns": ["Compound", "IC50 (µM)", "Probe substrate"], "rows": rows,
                              "notes": ["7-point curve, top 50 µM; ketoconazole control"]}


def _kinase(ctx: Ctx):
    r = rng_for(ctx.p.id, "kinase")
    base = 7.2 + rng_for(ctx.s.id, "kbase").gauss(0, 0.4)
    rows = []
    best = None
    for c in ctx.c:
        pic = base + _frag_effect(ctx.s, c["smiles"] + "kin", 0.6) + r.gauss(0, 0.1)
        ic = 10 ** (9 - pic)
        rows.append([c["id"], sig(ic, 2) if ic < 10000 else ">10000", f"{r.uniform(0.85, 1.25):.2f}"])
        best = ic if best is None else min(best, ic)
    ctx.tables["kinase_primary"] = {"title": f"{ctx.s.target} IC50 (nM)", "columns": ["Compound", "IC50 (nM)", "Hill slope"], "rows": rows,
                                    "notes": ["ATP at Km; 10-point, 3-fold; staurosporine control"]}
    ctx.values["kinase.best_ic50_nM"] = sig(best, 2)


def _kinase_panel(ctx: Ctx):
    r = rng_for(ctx.p.id, "kpanel")
    kinases = ["ABL1", "AURKA", "CDK2", "CHEK1", "EGFR", "FLT3", "GSK3B", "JAK2", "KDR", "LCK", "MAPK14", "PIK3CA", "SRC", "SYK", "BTK", "ROCK1"]
    picks = ctx.c[: min(6, len(ctx.c))]
    rows = []
    for k in kinases:
        rows.append([k] + [f"{max(0, min(100, r.gauss(25, 25))):.0f}" for _ in picks])
    ctx.tables["kinase_panel"] = {"title": "Kinase selectivity panel, % inhibition at 1 µM", "columns": ["Kinase"] + [c["id"] for c in picks], "rows": rows, "notes": []}


def _mic(ctx: Ctx):
    r = rng_for(ctx.p.id, "mic")
    p = ctx.pred("mic_clint")
    rows = []
    for i, c in enumerate(ctx.c):
        lg = (p[i] if p is not None else 1.2) + 0.12 * (c["clogp"] - 3) + _frag_effect(ctx.s, c["smiles"] + "mic", 0.2)
        h = 10 ** (lg + r.gauss(0, 0.08))
        rt = h * math.exp(r.gauss(0.5, 0.3))
        def disp(x):
            return "<3" if x < 3 else (">300" if x > 300 else sig(x, 2))
        th = 1386 / max(h, 0.1)
        rows.append([c["id"], disp(h), ">60" if th > 60 else sig(th, 2), disp(rt), ">60" if 1386 / max(rt, .1) > 60 else sig(1386 / rt, 2)])
    ctx.tables["mic_stab"] = {"title": "Liver microsomal stability (0.5 mg/mL protein, 1 µM)",
                              "columns": ["Compound", "Human CLint (µL/min/mg)", "Human t½ (min)", "Rat CLint (µL/min/mg)", "Rat t½ (min)"], "rows": rows,
                              "notes": ["Controls: verapamil (high), diltiazem (medium) within historical range"]}


def _hep(ctx: Ctx):
    r = rng_for(ctx.p.id, "hep")
    p = ctx.pred("hep_clint")
    rows = []
    for i, c in enumerate(ctx.c):
        lg = (p[i] if p is not None else 1.0) + _frag_effect(ctx.s, c["smiles"] + "hep", 0.2)
        v = 10 ** (lg + r.gauss(0, 0.1))
        rows.append([c["id"], "<2" if v < 2 else sig(v, 2), sig(v * math.exp(r.gauss(0.6, 0.3)), 2)])
    ctx.tables["hep_stab"] = {"title": "Cryopreserved hepatocyte stability (1 µM, 0.5×10^6 cells/mL)",
                              "columns": ["Compound", "Human CLint (µL/min/10^6 cells)", "Rat CLint (µL/min/10^6 cells)"], "rows": rows, "notes": []}


def _ppb(ctx: Ctx):
    r = rng_for(ctx.p.id, "ppb")
    p = ctx.pred("ppb")
    rows = []
    for i, c in enumerate(ctx.c):
        b = (p[i] if p is not None else 92) + 2.0 * (c["clogp"] - 3) + r.gauss(0, 1.2)
        b = max(40, min(99.9, b))
        rows.append([c["id"], f"{b:.1f}", f"{100 - b:.2f}", f"{r.uniform(80, 105):.0f}"])
    ctx.tables["ppb"] = {"title": "Human plasma protein binding (RED, 4 h, 37 °C)", "columns": ["Compound", "% bound", "fu", "Recovery (%)"], "rows": rows, "notes": ["Warfarin control 98-99% bound"]}


def _caco2(ctx: Ctx):
    r = rng_for(ctx.p.id, "caco2")
    p = ctx.pred("caco2")
    rows = []
    for i, c in enumerate(ctx.c):
        lp = (p[i] if p is not None else -5.3) - 0.004 * (c["tpsa"] - 80)
        ab = 10 ** (lp + 6 + r.gauss(0, 0.1))
        er = max(0.5, math.exp(r.gauss(0.4 + 0.3 * c["hbd"], 0.4)))
        rows.append([c["id"], sig(ab, 2), sig(ab * er, 2), sig(er, 2), f"{r.uniform(70, 102):.0f}"])
    ctx.tables["caco2"] = {"title": "Caco-2 bidirectional permeability (10 µM, pH 7.4)", "columns": ["Compound", "Papp A-B (10^-6 cm/s)", "Papp B-A (10^-6 cm/s)", "Efflux ratio", "Recovery (%)"], "rows": rows, "notes": []}


def _sol(ctx: Ctx):
    r = rng_for(ctx.p.id, "sol")
    p = ctx.pred("logs")
    rows = []
    for i, c in enumerate(ctx.c):
        logs = (p[i] if p is not None else -4.5) - 0.3 * (c["clogp"] - 3) + r.gauss(0, 0.2)
        um = 10 ** logs * 1e6
        rows.append([c["id"], "<1" if um < 1 else (">200" if um > 200 else sig(um, 2))])
    ctx.tables["solubility"] = {"title": "Kinetic solubility, PBS pH 7.4 (µM)", "columns": ["Compound", "Solubility (µM)"], "rows": rows, "notes": ["From 10 mM DMSO stock, 2% DMSO final, nephelometry"]}


def _pk(ctx: Ctx):
    r = rng_for(ctx.p.id, "pk")
    rows = []
    for c in ctx.c[: max(1, min(6, len(ctx.c)))]:
        cl = math.exp(r.gauss(3.0, 0.6))
        vss = math.exp(r.gauss(0.3, 0.5))
        th = 0.693 * vss * 1000 / 60 / cl
        f = max(2, min(95, r.gauss(35, 20)))
        rows.append([c["id"], sig(cl, 2), sig(vss, 2), sig(th, 2), f"{f:.0f}"])
    ctx.tables["rodent_pk"] = {"title": "Rat PK (1 mg/kg IV, 5 mg/kg PO; n=3)", "columns": ["Compound", "CL (mL/min/kg)", "Vss (L/kg)", "t½ (h)", "F (%)"], "rows": rows, "notes": ["LC-MS/MS, LLOQ 1 ng/mL"]}


def _synthesis(ctx: Ctx):
    r = rng_for(ctx.p.id, "syn")
    rows = []
    for c in ctx.c:
        rows.append([c["id"], c["smiles"], f"{c['mw']:.1f}", f"{max(4, min(88, r.gauss(42, 18))):.0f}", f"{max(90, min(99.8, r.gauss(97, 1.5))):.1f}", f"{max(5, r.gauss(28, 12)):.0f}"])
    ctx.tables["synthesis"] = {"title": "Compounds delivered", "columns": ["Compound", "SMILES", "MW", "Yield (%)", "Purity LCMS (%)", "Amount (mg)"], "rows": rows, "notes": []}


def _docking(ctx: Ctx):
    r = rng_for(ctx.p.id, "dock")
    rows = []
    for c in ctx.c:
        rows.append([c["id"], f"{r.gauss(-8.6, 0.9):.1f}", f"{max(0.5, r.gauss(1.6, 0.6)):.1f}", r.choice(["hinge H-bond", "hinge + gatekeeper", "solvent-exposed", "no hinge contact"])])
    ctx.tables["comp_screen"] = {"title": "Docking scores", "columns": ["Compound", "Score (kcal/mol)", "Pose RMSD vs ref (Å)", "Key interaction"], "rows": rows, "notes": []}


def _stability(ctx: Ctx):
    r = rng_for(ctx.p.id, "stab")
    tps = [0, 1, 3, 6, 9, 12, 18, 24]
    started = ctx.p.dates.start
    if started:
        months_avail = max(0, ((ctx.p.dates.completion or started.__class__(2026, 10, 8)) - started).days // 30)
        tps = [t for t in tps if t <= max(1, months_avail)] or [0]
    conds = [("25 °C/60% RH", 0.04), ("30 °C/65% RH", 0.07), ("40 °C/75% RH", 0.25)]
    rows = []
    a0 = r.uniform(99.2, 100.6)
    for cond, k in conds:
        for t in tps:
            if cond.startswith("40") and t > 6:
                continue
            a = a0 - k * t * r.uniform(0.7, 1.3) + r.gauss(0, 0.3)
            ia = max(0.02, 0.05 + 0.02 * k * t * 10 + r.gauss(0, 0.01))
            ib = max(0.0, 0.03 + 0.012 * k * t * 10 + r.gauss(0, 0.01))
            tot = ia + ib + r.uniform(0.05, 0.15)
            rows.append([cond, t, f"{a:.1f}", f"{ia:.2f}", "<0.05" if ib < 0.05 else f"{ib:.2f}", f"{tot:.2f}", f"{r.uniform(0.8, 2.5):.1f}", "Complies" if a >= 95 and tot <= 2 else "OOS - investigate"])
    ctx.tables["stability"] = {"title": "Stability results (assay % label claim; impurities % area)",
                               "columns": ["Condition", "Timepoint (months)", "Assay (% LC)", "Imp A RRT 0.86 (%)", "Imp B RRT 1.12 (%)", "Total impurities (%)", "Water KF (% w/w)", "Result"],
                               "rows": rows, "notes": ["Specification: assay 95.0-105.0% LC; any unspecified impurity ≤0.20%; total ≤2.0%"]}
    ctx.values["stability.t0_assay"] = f"{a0:.1f}"
    ctx.values["stability.last_timepoint_months"] = str(max(tps))


def _method_val(ctx: Ctx):
    r = rng_for(ctx.p.id, "mv")
    rows = [["Linearity (r²)", f"{r.uniform(0.9991, 0.9999):.4f}", "≥0.999"],
            ["Range (% nominal)", "50-150", "80-120 minimum"],
            ["Accuracy 80% (% recovery)", f"{r.gauss(99.6, 0.6):.1f}", "98.0-102.0"],
            ["Accuracy 100% (% recovery)", f"{r.gauss(100.1, 0.5):.1f}", "98.0-102.0"],
            ["Accuracy 120% (% recovery)", f"{r.gauss(100.3, 0.6):.1f}", "98.0-102.0"],
            ["Repeatability (%RSD, n=6)", f"{r.uniform(0.2, 0.8):.2f}", "≤2.0"],
            ["Intermediate precision (%RSD)", f"{r.uniform(0.5, 1.3):.2f}", "≤2.0"],
            ["LOQ (% of nominal)", f"{r.uniform(0.02, 0.05):.2f}", "≤0.05"]]
    ctx.tables["method_val"] = {"title": "Method validation summary", "columns": ["Parameter", "Result", "Acceptance"], "rows": rows, "notes": []}


def _formulation(ctx: Ctx):
    r = rng_for(ctx.p.id, "form")
    vehicles = ["0.5% methylcellulose", "0.5% HPMC / 0.1% Tween 80", "20% HP-β-CD in water", "PEG400/water 30:70", "10% DMSO / 90% corn oil",
                "Labrasol/PEG400 1:1", "5% NMP / 15% Solutol HS15 / 80% water", "pH 4 citrate buffer"]
    rows = []
    for v in vehicles:
        s = math.exp(r.gauss(0.5, 1.2))
        rows.append([v, sig(s, 2), r.choice(["Clear solution", "Fine suspension", "Suspension, settles <1 h", "Precipitate at 24 h", "Clear, slight yellow tint"]), r.choice(["Stable", "Stable", "Crystal growth at 24 h", "Not assessed"])])
    ctx.tables["form_screen"] = {"title": "Vehicle screen (target 10 mg/mL)", "columns": ["Vehicle", "Solubility (mg/mL)", "Appearance", "24 h physical stability"], "rows": rows, "notes": []}


def _cytotox(ctx: Ctx):
    r = rng_for(ctx.p.id, "ctox")
    rows = []
    for c in ctx.c:
        ic = math.exp(r.gauss(3.6 - 0.25 * (c["clogp"] - 3), 0.8))
        rows.append([c["id"], ">100" if ic > 100 else sig(ic, 2), ">100" if ic * 0.7 > 100 else sig(ic * 0.7, 2)])
    ctx.tables["cytotox"] = {"title": "HepG2 cytotoxicity (ATP content), IC50 µM", "columns": ["Compound", "24 h IC50 (µM)", "48 h IC50 (µM)"], "rows": rows, "notes": ["Chlorpromazine control"]}


def _ames(ctx: Ctx):
    r = rng_for(ctx.p.id, "ames")
    strains = ["TA98", "TA100", "TA1535", "TA1537", "WP2 uvrA (pKM101)"]
    base = {"TA98": 25, "TA100": 110, "TA1535": 14, "TA1537": 9, "WP2 uvrA (pKM101)": 140}
    doses = [0, 15.8, 50, 158, 500, 1580, 5000]
    rows = []
    for s in strains:
        for s9 in ["-S9", "+S9"]:
            for d in doses:
                m = base[s] * r.uniform(0.85, 1.2)
                rows.append([s, s9, "vehicle" if d == 0 else d, f"{m:.0f}", f"{m * 0.12:.0f}", f"{m / base[s]:.2f}"])
    ctx.tables["ames"] = {"title": "Ames test, mean revertants/plate (n=3)", "columns": ["Strain", "Activation", "Dose (µg/plate)", "Mean", "SD", "Fold vs vehicle"], "rows": rows, "notes": ["Positive controls valid in all strains; outcome: negative"]}
    ctx.values["ames.outcome"] = "negative"


def _mn(ctx: Ctx):
    r = rng_for(ctx.p.id, "mn")
    rows = []
    for tr in ["3 h +S9", "3 h -S9", "24 h -S9"]:
        for d in [0, 50, 100, 200]:
            rows.append([tr, "vehicle" if d == 0 else d, f"{max(0.2, r.gauss(0.9, 0.25)):.2f}", f"{max(0, 100 - d * r.uniform(0.05, 0.2)):.0f}"])
    ctx.tables["micronucleus"] = {"title": "In vitro micronucleus (TK6), % MN cells", "columns": ["Treatment", "Conc (µg/mL)", "% MN cells", "RPD (%)"], "rows": rows, "notes": ["Outcome: negative"]}


def _drf(ctx: Ctx):
    r = rng_for(ctx.p.id, "drf")
    rows = []
    for d in [0, 30, 100, 300]:
        bw = r.gauss(8 - d * 0.03, 2)
        rows.append([d, "3M/3F", f"{bw:+.1f}", "None" if d < 300 else r.choice(["Piloerection, hunched posture days 3-5", "Reduced activity; 1F euthanised day 4"])])
    ctx.tables["drf"] = {"title": "7-day rat dose-range finding", "columns": ["Dose (mg/kg/day)", "Animals", "Body weight change day 1-7 (%)", "Clinical observations"], "rows": rows, "notes": ["MTD estimated at 100 mg/kg/day"]}
    ctx.values["drf.mtd"] = "100 mg/kg/day"


GEN = {"herg": _herg, "cyp_inhib": _cyp, "cyp_ic50": _cyp_ic50, "kinase_primary": _kinase, "kinase_panel": _kinase_panel,
       "mic_stab": _mic, "hep_stab": _hep, "ppb": _ppb, "caco2": _caco2, "solubility": _sol, "rodent_pk": _pk,
       "synthesis": _synthesis, "comp_screen": _docking, "stability": _stability, "method_val": _method_val,
       "form_screen": _formulation, "cytotox": _cytotox, "ames": _ames, "micronucleus": _mn, "drf": _drf}


def _benchmark(ctx: Ctx, w):
    p = ctx.p
    v = ctx.values
    rows = [["Project", p.firm_project_id], ["Client", p.client_variant], ["Compounds tested", str(p.n_compounds)],
            ["Series / chemotype", f"{ctx.s.name} ({ctx.s.chemotype})" if ctx.s else "-"],
            ["Assays", ", ".join(w.assays[a]["name"] for a in p.assays)],
            ["Turnaround (calendar days)", str(p.turnaround_days) if p.turnaround_days is not None else "-"],
            ["Price", f"{p.price.currency} {p.price.amount:,.0f}"]]
    if "herg.n_tested" in v:
        rows += [["hERG IC50 <1 µM", v["herg.n_lt_1uM"]], ["hERG IC50 1-10 µM", v["herg.n_1_10uM"]], ["hERG IC50 ≥10 µM", v["herg.n_ge_10uM"]],
                 ["hERG median IC50 (µM)", v["herg.median_ic50_uM"]], ["E-4031 control IC50 (nM)", v["herg.control_e4031_nM"]]]
    if "cyp.n_any_gt50" in v:
        rows += [[f"{iso} >50% inhibition @10 µM", v[f"cyp.n_gt50_{iso}"]] for iso in CYPS]
        rows += [["Compounds with any CYP >50%", v["cyp.n_any_gt50"]], ["Ketoconazole (3A4) IC50 (µM)", v["cyp.control_CYP3A4_uM"]]]
    ctx.tables["benchmark"] = {"title": "Project benchmark summary", "columns": ["Metric", "Value"], "rows": rows, "notes": []}
    for r_ in rows:
        pass


def generate() -> str:
    errs: list[str] = []
    w = load_world(errs)
    if errs:
        return "world has load errors; run `mockgen world validate` first:\n" + "\n".join(errs[:20])
    NUMBERS.mkdir(exist_ok=True)
    allc = {}
    for sid, s in w.series.items():
        allc[sid] = series_compounds(s)
    (NUMBERS / "compounds.json").write_text(json.dumps(allc, indent=1, ensure_ascii=False))
    n = 0
    for pid, p in sorted(w.projects.items()):
        s = w.series.get(p.series_id) if p.series_id else None
        cmpds = []
        if s and p.n_compounds:
            pool = allc[s.id]
            r = rng_for(pid, "pick")
            idx = sorted(r.sample(range(len(pool)), min(p.n_compounds, len(pool))))
            cmpds = [pool[i] for i in idx]
        ctx = Ctx(p, s, cmpds)
        has_results = p.status in ("completed", "in_progress", "on_hold", "cancelled")
        if has_results:
            for a in p.assays:
                if a in GEN and (cmpds or a in ("stability", "method_val", "form_screen", "drf")):
                    GEN[a](ctx)
            if p.status in ("in_progress", "on_hold", "cancelled"):
                # partial results: keep first ~40-70% of rows
                r = rng_for(pid, "partial")
                for k, t in ctx.tables.items():
                    keep = max(1, int(len(t["rows"]) * r.uniform(0.4, 0.7)))
                    t["rows"] = t["rows"][:keep]
                    t["notes"].append(f"INTERIM: {keep} of {len(cmpds) or keep} results reported; remaining in progress" if p.status == "in_progress" else "Work stopped; partial data only")
        if s:
            _benchmark(ctx, w)
        ctx.values.update({"price": f"{p.price.currency} {p.price.amount:,.0f}", "n_compounds": str(p.n_compounds),
                           "turnaround_days": str(p.turnaround_days) if p.turnaround_days is not None else "",
                           "client_variant": p.client_variant, "project_id": p.firm_project_id, "lims_id": p.lims_id})
        out = {"project_id": pid, "firm": p.firm, "status": p.status, "series": s.id if s else None,
               "compounds": [{k: c[k] for k in ("id", "smiles", "mw", "clogp", "tpsa")} for c in cmpds],
               "tables": ctx.tables, "values": ctx.values}
        (NUMBERS / f"{pid}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
        n += 1
    avail = admet.available()
    used = [k for k, v in avail.items() if v]
    return f"numbers: {n} projects, {sum(len(v) for v in allc.values())} enumerated compounds in {len(allc)} series; public-data models: {', '.join(used) or 'none (parametric fallback)'}"
