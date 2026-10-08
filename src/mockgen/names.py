"""Blocklist and registered-name checks."""
from __future__ import annotations

import re
from functools import lru_cache

import yaml
from rapidfuzz import fuzz

from .paths import CONFIG

PERSON_BLOCK = ["Jim Thompson", "James Thompson", "Thompson"]


class Blocklist:
    def __init__(self, terms: list[str]):
        self.terms = sorted(set(terms), key=len, reverse=True)
        self.short = [t for t in self.terms if len(t) <= 4 or t.isupper()]  # acronyms: exact, case-sensitive
        self.long = [t for t in self.terms if t not in self.short]
        self._re_short = re.compile(r"\b(" + "|".join(re.escape(t) for t in self.short) + r")\b") if self.short else None
        self._re_long = re.compile(r"\b(" + "|".join(re.escape(t) for t in self.long) + r")\b", re.I) if self.long else None

    @classmethod
    @lru_cache(maxsize=1)
    def load(cls) -> "Blocklist":
        raw = yaml.safe_load((CONFIG / "blocklist.yaml").read_text())
        terms = []
        for v in raw.values():
            terms.extend(v)
        terms.extend(PERSON_BLOCK)
        return cls(terms)

    def scan_text(self, text: str) -> list[str]:
        hits = []
        if self._re_short:
            hits += [m.group(1) for m in self._re_short.finditer(text)]
        if self._re_long:
            hits += [m.group(1) for m in self._re_long.finditer(text)]
        return sorted(set(hits))

    def check_name(self, name: str, person: bool = False) -> str | None:
        hits = self.scan_text(name)
        if hits:
            return "exact: " + ", ".join(hits)
        # fuzzy: compare distinctive tokens (len>=5) against long terms
        toks = [t for t in re.findall(r"[A-Za-z][A-Za-z'\-]+", name) if len(t) >= 5]
        generic = {"pharma", "pharmaceuticals", "therapeutics", "biosciences", "bioscience", "discovery", "analytical",
                   "laboratories", "sciences", "biotech", "limited", "group", "holdings", "research", "medicines",
                   "biologics", "health", "chemistry", "services", "consulting", "partners", "institute", "university"}
        for tok in toks:
            if tok.lower() in generic:
                continue
            for term in self.long:
                for tt in term.split():
                    if len(tt) < 5 or tt.lower() in generic:
                        continue
                    if fuzz.ratio(tok.lower(), tt.lower()) >= 88:
                        return f"fuzzy: '{tok}' ~ '{term}'"
        return None
