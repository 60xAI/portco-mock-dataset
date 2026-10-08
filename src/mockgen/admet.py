"""Simple ADMET value models trained on public TDC benchmark sets (records never copied).

Datasets (Therapeutics Data Commons, Harvard Dataverse; ChEMBL/PubChem-derived, CC BY / CC BY-SA):
herg_karim, cyp{1a2,2c9,2c19,2d6,3a4}_veith, clearance_microsome_az, clearance_hepatocyte_az,
caco2_wang, solubility_aqsoldb, ppbr_az, lipophilicity_astrazeneca.
If a file is missing, `predict` returns None and callers fall back to property-based trends.
"""
from __future__ import annotations

import csv
import pickle
from functools import lru_cache

import numpy as np
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import rdFingerprintGenerator, Descriptors, Crippen, rdMolDescriptors
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

from .paths import ROOT

PUBLIC = ROOT / "data" / "public"
MODELS = ROOT / "data" / "models"

SETS = {
    "herg": ("herg_karim", "clf"),
    "cyp1a2": ("cyp1a2_veith", "clf"),
    "cyp2c9": ("cyp2c9_veith", "clf"),
    "cyp2c19": ("cyp2c19_veith", "clf"),
    "cyp2d6": ("cyp2d6_veith", "clf"),
    "cyp3a4": ("cyp3a4_veith", "clf"),
    "mic_clint": ("clearance_microsome_az", "reg_log"),
    "hep_clint": ("clearance_hepatocyte_az", "reg_log"),
    "caco2": ("caco2_wang", "reg"),
    "logs": ("solubility_aqsoldb", "reg"),
    "ppb": ("ppbr_az", "reg"),
    "logd": ("lipophilicity_astrazeneca", "reg"),
}
RDLogger.DisableLog("rdApp.*")
_gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=1024)


def featurize(smiles: str):
    m = Chem.MolFromSmiles(smiles)
    if m is None:
        return None
    fp = _gen.GetFingerprintAsNumPy(m).astype(np.float32)
    desc = np.array([Descriptors.MolWt(m) / 100, Crippen.MolLogP(m), rdMolDescriptors.CalcTPSA(m) / 20,
                     rdMolDescriptors.CalcNumHBD(m), rdMolDescriptors.CalcNumHBA(m),
                     rdMolDescriptors.CalcNumAromaticRings(m), rdMolDescriptors.CalcFractionCSP3(m) * 5], dtype=np.float32)
    return np.concatenate([fp, desc])


def _read(name, max_rows=6000):
    p = PUBLIC / f"{name}.tab"
    if not p.exists():
        return None
    X, y = [], []
    with p.open() as fh:
        r = csv.reader(fh, delimiter="\t")
        header = next(r)
        si = 1
        for i, row in enumerate(r):
            if len(row) < 3:
                continue
            if name == "ppbr_az" and len(row) > 3 and "sapiens" not in row[3]:
                continue
            try:
                yv = float(row[2])
            except ValueError:
                continue
            f = featurize(row[si])
            if f is None:
                continue
            X.append(f)
            y.append(yv)
    if not X:
        return None
    X, y = np.array(X), np.array(y)
    if len(X) > max_rows:
        idx = np.random.RandomState(0).choice(len(X), max_rows, replace=False)
        X, y = X[idx], y[idx]
    return X, y


@lru_cache(maxsize=None)
def model(key: str):
    MODELS.mkdir(parents=True, exist_ok=True)
    cache = MODELS / f"{key}.pkl"
    if cache.exists():
        return pickle.loads(cache.read_bytes())
    name, kind = SETS[key]
    data = _read(name)
    if data is None:
        return None
    X, y = data
    if kind == "clf":
        m = RandomForestClassifier(n_estimators=120, min_samples_leaf=2, n_jobs=-1, random_state=0)
        m.fit(X, y.astype(int))
    else:
        if kind == "reg_log":
            y = np.log10(np.clip(y, 0.5, None))
        m = RandomForestRegressor(n_estimators=120, min_samples_leaf=2, n_jobs=-1, random_state=0)
        m.fit(X, y)
    cache.write_bytes(pickle.dumps(m))
    return m


def predict(key: str, smiles_list: list[str]):
    m = model(key)
    if m is None:
        return None
    X = np.array([featurize(s) for s in smiles_list])
    if SETS[key][1] == "clf":
        return m.predict_proba(X)[:, 1]
    return m.predict(X)


def available() -> dict[str, bool]:
    return {k: (PUBLIC / f"{v[0]}.tab").exists() for k, v in SETS.items()}
