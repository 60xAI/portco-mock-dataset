"""Background staff from Faker (deterministic), appended to world/people.yaml."""
from __future__ import annotations

import random
import zlib
from datetime import date, timedelta

import yaml
from faker import Faker

from .paths import SEED, TODAY, WORLD
from .names import Blocklist
from .world import load_world

LOCALES = [("en_GB", 30), ("en_US", 18), ("en_IE", 4), ("de_DE", 5), ("fr_FR", 5), ("it_IT", 5), ("es_ES", 4),
           ("pl_PL", 4), ("nl_NL", 3), ("pt_PT", 2), ("sv_SE", 2), ("en_IN", 8), ("east_asian", 6), ("it_IT", 2)]
NATIONALITY = {"en_GB": "British", "en_US": "American", "en_IE": "Irish", "de_DE": "German", "fr_FR": "French",
               "it_IT": "Italian", "es_ES": "Spanish", "pl_PL": "Polish", "nl_NL": "Dutch", "pt_PT": "Portuguese",
               "sv_SE": "Swedish", "en_IN": "Indian", "el_GR": "Greek", "east_asian": ""}
EAST_ASIAN = {
    "Chinese": (["Wei", "Li", "Jing", "Hao", "Xin", "Yan", "Lei", "Mei", "Jun", "Ying", "Chen", "Lin"],
                ["Zhang", "Wang", "Liu", "Huang", "Zhao", "Wu", "Zhou", "Xu", "Sun", "Ma", "Hu", "Guo"]),
    "Korean": (["Min-jun", "Seo-yeon", "Ji-ho", "Hye-jin", "Sung-min", "Eun-ji"], ["Kim", "Park", "Choi", "Jung", "Kang", "Yoon"]),
    "Japanese": (["Haruka", "Kenji", "Yuki", "Takeshi", "Aiko", "Daisuke"], ["Sato", "Suzuki", "Takahashi", "Watanabe", "Ito", "Nakamura"]),
}
TITLES = {
    "medchem": ["Chemist", "Senior Chemist", "Principal Scientist", "Team Leader, Chemistry", "Synthetic Chemist", "Associate Director, Chemistry"],
    "invitro": ["Research Scientist", "Senior Scientist", "Study Director", "Assay Biologist", "Electrophysiologist", "Laboratory Technician"],
    "dmpk": ["Bioanalyst", "DMPK Scientist", "Senior DMPK Scientist", "Study Director, DMPK", "Mass Spectrometry Specialist"],
    "compchem": ["Bioinformatician", "Computational Chemist", "Data Scientist", "Senior Bioinformatician"],
    "analytical": ["Analytical Chemist", "QC Analyst", "Stability Coordinator", "Senior Analyst", "QA Officer"],
    "formulation": ["Formulation Scientist", "Pre-formulation Scientist", "Senior Formulation Scientist", "CMC Lead"],
    "tox": ["Study Director", "Toxicologist", "Senior Toxicologist", "In Vivo Technician", "Genetic Toxicologist", "Pathology Coordinator"],
    "admin": ["Business Development Manager", "Office Manager", "Finance Manager", "Quality Assurance Manager", "Project Manager", "HR Advisor", "IT Support Analyst", "Sample Management Coordinator"],
    "HO": ["Group Finance Director", "Group HR Business Partner", "Integration PMO Analyst", "Group Commercial Director", "Head of Group Marketing", "Group IT Manager", "Group Financial Controller", "Executive Assistant", "Group Quality Director", "Commercial Analyst"],
}
TARGET = {"A": 30, "B": 34, "C": 30, "D": 20, "E": 25, "F": 18, "G": 25, "HO": 13}


def username(style: str, first: str, last: str) -> str:
    def clean(s):
        return "".join(ch for ch in s.lower() if ch.isalpha())
    import unicodedata
    fold = lambda s: "".join(c for c in unicodedata.normalize("NFKD", s.replace("ł", "l").replace("ø", "o").replace("ß", "ss")) if not unicodedata.combining(c)) if False else "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    f, l = clean(fold(first)), clean(fold(last))
    return (style.replace("{first}", f).replace("{last}", l).replace("{f}", f[:1]).replace("{l}", l[:1]))


def fill_staff(total: int = 200) -> str:
    errs: list[str] = []
    w = load_world(errs, upto="people")
    if not w.firms or not w.group:
        return "need group and firms stages first"
    raw = yaml.safe_load((WORLD / "people.yaml").read_text()) or {}
    people = [p for p in raw.get("people", []) if not str(p.get("id", "")).startswith("BG")]
    existing_users = {p["username"] for p in people}
    existing_names = {p["canonical_name"] for p in people}
    rnd = random.Random(SEED)
    fakers = {loc: Faker(loc) for loc, _ in LOCALES if loc != "east_asian"}
    for loc, fk in fakers.items():
        fk.seed_instance(SEED + zlib.crc32(loc.encode()) % 1000)
    bl = Blocklist.load()
    counts = {u: 0 for u in TARGET}
    for p in people:
        counts[p["home_firm"]] = counts.get(p["home_firm"], 0) + 1
    need = max(0, total - len(people))
    scale = need / max(1, sum(max(0, TARGET[u] - counts.get(u, 0)) for u in TARGET))
    plan = {u: round(max(0, TARGET[u] - counts.get(u, 0)) * scale) for u in TARGET}
    out = []
    n = 0
    locs, weights = zip(*LOCALES)
    for unit, k in plan.items():
        for _ in range(k):
            for _attempt in range(50):
                loc = rnd.choices(locs, weights)[0]
                if loc == "east_asian":
                    nat = rnd.choice(list(EAST_ASIAN))
                    first, last = rnd.choice(EAST_ASIAN[nat][0]), rnd.choice(EAST_ASIAN[nat][1])
                else:
                    nat = NATIONALITY[loc]
                    fk = fakers[loc]
                    first, last = fk.first_name(), fk.last_name()
                name = f"{first} {last}"
                if " " in last or "-" in last and rnd.random() < 0.5:
                    continue
                if bl.check_name(name, person=True) or name in existing_names:
                    continue
                if unit == "HO":
                    style = "{first}.{last}"
                    start = w.group.formed
                    firm_letter = None
                else:
                    firm = w.firms[unit]
                    style = firm.username_style
                    start = max(firm.founded, date(firm.file_era_start, 1, 1))
                    firm_letter = unit
                u = username(style, first, last)
                if u in existing_users:
                    continue
                break
            existing_users.add(u)
            existing_names.add(name)
            if unit == "HO":
                sl = "admin"
                titles = TITLES["HO"]
            else:
                firm = w.firms[unit]
                sl = rnd.choice(firm.service_lines) if rnd.random() > 0.2 else "admin"
                titles = TITLES.get(sl, TITLES["admin"])
            span = (TODAY - timedelta(days=60) - start).days
            joined = start + timedelta(days=rnd.randint(0, max(1, span)))
            left = None
            if rnd.random() < 0.38 and (TODAY - joined).days > 400:
                left = joined + timedelta(days=rnd.randint(365, max(366, (TODAY - joined).days - 1)))
            end = left
            # role history: 1-2 spells; G staff stay at G; others may move to HO after the group exists
            roles = []
            t1 = rnd.choice(titles)
            unit_code = unit
            if (end or TODAY) - joined > timedelta(days=4 * 365) and rnd.random() < 0.45:
                mid = joined + timedelta(days=rnd.randint(700, max(701, ((end or TODAY) - joined).days - 200)))
                t2 = rnd.choice([t for t in titles if t != t1] or titles)
                roles.append({"title": t1, "unit": unit_code, "from": joined, "to": mid - timedelta(days=1)})
                roles.append({"title": t2, "unit": unit_code, "from": mid, "to": end})
            else:
                roles.append({"title": t1, "unit": unit_code, "from": joined, "to": end})
            doctor = sl not in ("admin",) and rnd.random() < 0.45
            n += 1
            initial = first[0]
            variants = [f"{'Dr ' if doctor else ''}{initial}. {last}", name, u]
            out.append({
                "id": f"BG{n:03d}", "canonical_name": name, "first_name": first, "last_name": last,
                "title": "Dr" if doctor else None, "variants": variants, "username": u,
                "home_firm": unit, "service_line": sl, "roles": roles, "joined": joined, "left": left,
                "key": False, "nationality": nat,
            })
    raw["people"] = people + out
    (WORLD / "people.yaml").write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True, width=120))
    return f"added {len(out)} background staff; total {len(raw['people'])}"
