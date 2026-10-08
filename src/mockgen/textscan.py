"""Text extraction from content JSON and name/date scanning."""
from __future__ import annotations

import re
from datetime import date
from functools import lru_cache

SKIP_KEYS = {"layout", "kind", "ref", "table_ref", "family", "style", "at", "cell", "fmt", "fill", "color", "tab_color", "chart_at",
             "start", "orientation", "number_formats", "col_widths", "merged", "freeze"}


def strings(obj, skip=SKIP_KEYS):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in skip:
                continue
            yield from strings(v, skip)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v, skip)


def all_text(obj) -> str:
    return "\n".join(strings(obj))


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip().lower()


COMPANY_SUFFIX = (r"Pharma|Pharmaceuticals|Therapeutics|Biosciences|Bioscience|Biotech|Biologics|Medicines|Discovery|Laboratories|Labs|"
                  r"Analytical|Computational|Toxicology|Bioanalysis|Sciences|Ltd|Limited|plc|Inc|GmbH|AG|SAS|BV|AB|ApS|SpA|LLC|Corp|Corporation|Holdings")
COMPANY_RE = re.compile(r"\b([A-Z][A-Za-z'\-]+)(?:[ \t]+(?:[A-Z][A-Za-z'\-]+|&))*[ \t]+(?:" + COMPANY_SUFFIX + r")\b")
COMMON = set("""the a an our your their its this that these those drug early late lead hit integrated contract medicinal computational analytical
structural chemical discovery clinical preclinical partner client clients global group in vitro vivo safety small molecule kinase new legacy former
combined shared central regional north south east west european american uk us british research development dmpk chemistry biology biologics
cro cdmo pharma biotech mid big large top virtual academic generic generics specialty animal health human rat dog mouse services service
platform portfolio business commercial company companies quality strategic translational and or of for with to from at by on as is are be was
were has have had not all any each other another more most many several some data science scientific bioinformatics bioanalysis toxicology
toxicological formulation formulations stability laboratories laboratory labs sciences medicines therapeutics pharmaceuticals biosciences
bioscience holdings limited corporation inc ltd plc gmbh ag bv ab llc corp tarnovell one key target targets oncology immunology respiratory
cns cardiovascular metabolic infectious rare disease diseases inflammation fibrosis neuroscience dermatology ophthalmology emerging established
existing prospective potential named listed unnamed undisclosed confidential senior junior principal head lead director manager scientist biologist chemist associate assistant chief group deputy acting interim""".split())

DR_RE = re.compile(r"\b(?:Dr|Prof|Professor)\.?\s+(?:[A-Z]\.\s*){0,2}([A-Z][a-z]+(?:[-'][A-Z][a-z]+)?)\b")
FULLNAME_RE = re.compile(r"\b([A-Z][a-z]+(?:-[A-Z][a-z]+)?)[ \t]+([A-Z][a-z]+(?:[-'][A-Z][a-z]+)?)\b")


@lru_cache(maxsize=1)
def faker_first_names() -> frozenset:
    names = set()
    try:
        from faker.providers.person.en_GB import Provider as GB
        from faker.providers.person.en_US import Provider as US
        for P in (GB, US):
            for attr in ("first_names", "first_names_male", "first_names_female"):
                v = getattr(P, attr, None)
                if v:
                    names.update(v.keys() if isinstance(v, dict) else v)
    except Exception:
        pass
    return frozenset(n for n in names if len(n) > 2)


MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
D_ISO = re.compile(r"\b(19[89]\d|20[0-3]\d)-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b")
D_SLASH = re.compile(r"\b(0?[1-9]|[12]\d|3[01])[/.](0?[1-9]|1[0-2])[/.](19[89]\d|20[0-3]\d)\b")
D_SLASH_US = re.compile(r"\b(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/(19[89]\d|20[0-3]\d)\b")
D_TEXT = re.compile(r"\b(0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?,?\s+(19[89]\d|20[0-3]\d)\b")
D_TEXT_US = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+(0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?,?\s+(19[89]\d|20[0-3]\d)\b")


def find_dates(text: str, us: bool = False) -> list[tuple[str, date]]:
    out = []

    def ok(y, m, d, raw):
        try:
            out.append((raw, date(int(y), int(m), int(d))))
        except ValueError:
            pass
    for m in D_ISO.finditer(text):
        ok(m.group(1), m.group(2), m.group(3), m.group(0))
    if us:
        for m in D_SLASH_US.finditer(text):
            ok(m.group(3), m.group(1), m.group(2), m.group(0))
    else:
        for m in D_SLASH.finditer(text):
            ok(m.group(3), m.group(2), m.group(1), m.group(0))
    for m in D_TEXT.finditer(text):
        ok(m.group(3), MONTHS[m.group(2)[:3].lower()], m.group(1), m.group(0))
    for m in D_TEXT_US.finditer(text):
        ok(m.group(3), MONTHS[m.group(1)[:3].lower()], m.group(2), m.group(0))
    return out


# eponymous methods and terms that look like person names
ALLOW_NAMES = {"karl fischer", "michaelis menten", "mann whitney", "hardy weinberg", "henderson hasselbalch", "lineweaver burk",
               "hill slope", "bland altman", "kaplan meier", "fisher exact", "wilcoxon rank", "student t", "dean stark", "grignard reagent"}
