"""Compound series enumeration with RDKit (deterministic)."""
from __future__ import annotations

import itertools
import random
from functools import lru_cache

from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, Crippen, rdMolDescriptors

RDLogger.DisableLog("rdApp.*")


def _attach(core: Chem.Mol, frags: dict[int, Chem.Mol]) -> Chem.Mol | None:
    """Join fragments onto core at matching map numbers ([*:n] on both sides)."""
    combo = core
    for n, frag in frags.items():
        combo = Chem.CombineMols(combo, frag)
    rw = Chem.RWMol(combo)
    dummies: dict[int, list[int]] = {}
    for a in rw.GetAtoms():
        if a.GetAtomicNum() == 0 and a.GetAtomMapNum():
            dummies.setdefault(a.GetAtomMapNum(), []).append(a.GetIdx())
    to_remove = []
    for n, idxs in dummies.items():
        if len(idxs) != 2:
            return None
        d1, d2 = idxs
        n1 = [x.GetIdx() for x in rw.GetAtomWithIdx(d1).GetNeighbors()]
        n2 = [x.GetIdx() for x in rw.GetAtomWithIdx(d2).GetNeighbors()]
        if len(n1) != 1 or len(n2) != 1:
            return None
        rw.AddBond(n1[0], n2[0], Chem.BondType.SINGLE)
        to_remove += [d1, d2]
    for i in sorted(to_remove, reverse=True):
        rw.RemoveAtom(i)
    m = rw.GetMol()
    try:
        Chem.SanitizeMol(m)
    except Exception:
        return None
    return m


def check_series(s) -> list[str]:
    errs = []
    core = Chem.MolFromSmiles(s.core_smiles)
    if core is None:
        return [f"core_smiles does not parse: {s.core_smiles}"]
    maps = sorted({a.GetAtomMapNum() for a in core.GetAtoms() if a.GetAtomicNum() == 0})
    if not maps or 0 in maps:
        errs.append("core needs mapped attachment points like [*:1]")
    for k in s.r_groups:
        if int(k) not in maps:
            errs.append(f"r_groups key {k} has no [*:{k}] on core")
    for m in maps:
        if str(m) not in s.r_groups:
            errs.append(f"attachment [*:{m}] has no r_groups list")
    for k, frags in s.r_groups.items():
        for f in frags:
            fm = Chem.MolFromSmiles(f)
            if fm is None:
                errs.append(f"r-group {k} fragment does not parse: {f}")
                continue
            dm = [a.GetAtomMapNum() for a in fm.GetAtoms() if a.GetAtomicNum() == 0]
            if dm != [int(k)]:
                errs.append(f"r-group {k} fragment {f} must have exactly one [*:{k}]")
    if not errs:
        n = len(enumerate_series(s))
        if n < 12:
            errs.append(f"series enumerates only {n} valid compounds; need >=12")
    return errs


def enumerate_series(s, limit: int = 400) -> list[dict]:
    key = (s.id, s.core_smiles, tuple((k, tuple(v)) for k, v in sorted(s.r_groups.items())))
    return list(_enum(key, s.compound_prefix, limit))


@lru_cache(maxsize=256)
def _enum(key, prefix, limit):
    sid, core_smi, rg = key
    core = Chem.MolFromSmiles(core_smi)
    lists = [[(int(k), Chem.MolFromSmiles(f)) for f in frags] for k, frags in rg]
    combos = list(itertools.product(*lists))
    rnd = random.Random(f"{sid}-enum")
    rnd.shuffle(combos)
    out, seen = [], set()
    for combo in combos:
        m = _attach(core, {k: f for k, f in combo})
        if m is None:
            continue
        smi = Chem.MolToSmiles(m)
        if smi in seen:
            continue
        seen.add(smi)
        out.append(smi)
        if len(out) >= limit:
            break
    res = []
    for i, smi in enumerate(out):
        m = Chem.MolFromSmiles(smi)
        res.append({
            "smiles": smi,
            "mw": round(Descriptors.MolWt(m), 1),
            "clogp": round(Crippen.MolLogP(m), 2),
            "tpsa": round(rdMolDescriptors.CalcTPSA(m), 1),
            "hbd": rdMolDescriptors.CalcNumHBD(m),
            "hba": rdMolDescriptors.CalcNumHBA(m),
            "basic_n": _basic_n(m),
            "arom_rings": rdMolDescriptors.CalcNumAromaticRings(m),
        })
    return tuple(res)


_BASIC = Chem.MolFromSmarts("[NX3;H2,H1,H0;!$(NC=O);!$(N-a);!$(N-S(=O)=O);!$(N#*);!$(N=*)]")


def _basic_n(m) -> int:
    return len(m.GetSubstructMatches(_BASIC))


def series_capacity(s) -> int:
    return len(enumerate_series(s))
