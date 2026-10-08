"""World store: pydantic records, loader and stage validation."""
from __future__ import annotations

import re
from collections import Counter
from datetime import date
from functools import lru_cache
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .paths import TODAY, WORLD
from . import names as namecheck

STAGES = ["group", "firms", "people", "clients", "projects", "compounds"]
FIRM_LETTERS = list("ABCDEFG")
ORG_UNITS = FIRM_LETTERS + ["HO"]


class M(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Location(M):
    city: str
    country: str


class Template(M):
    id: str
    kind: Literal["legacy", "transition", "group"]
    from_: date = Field(alias="from")
    to: Optional[date] = None
    primary_colour: str
    secondary_colour: str
    accent_colour: Optional[str] = None
    font_heading: str
    font_body: str
    footer_text: str
    brand_line: str  # e.g. "Ashcombe Discovery" or "Ashcombe Discovery, a Tarnovell company"
    notes: str = ""


class Workstream(M):
    name: str
    status: Literal["complete", "in_progress", "not_started", "paused"]
    notes: str = ""


class Integration(M):
    name: str
    started: date
    lead: str  # person id
    status: str
    workstreams: list[Workstream]


class Group(M):
    name: str
    short_name: str
    legal_name: str
    formed: date
    head_office: Location
    share_root: str
    email_domain: str
    brand_line_pattern: str  # e.g. "{firm}, a Tarnovell company"
    template: Template
    integration: Integration
    history: list[str] = []


class NamingStyle(M):
    description: str
    folder_examples: list[str]
    filename_examples: list[str]


class IdFormats(M):
    project_id: str  # human description + example, e.g. "BX-yy-nnn, e.g. BX-12-041"
    project_id_regex: str
    lims_id: str
    lims_id_regex: str
    report_id: str = ""


class Firm(M):
    letter: Literal["A", "B", "C", "D", "E", "F", "G"]
    legacy_name: str
    short_name: str
    service_focus: str
    service_lines: list[str]
    role: Literal["founder", "acquired", "held_back"]
    founded: date
    joined_group: date  # A: group formation; G: Oct 2026
    location: Location
    date_convention: Literal["UK", "US"]
    date_formats: list[str]
    units_notes: str
    share_root: str
    naming_style: NamingStyle
    id_formats: IdFormats
    username_style: str
    email_domain: str
    voice: str
    terminology: dict[str, str]
    typical_lengths: dict[str, str]
    templates: list[Template]
    transition_rules: str
    file_era_start: int
    history: list[str] = []


class RoleSpell(M):
    title: str
    unit: str  # firm letter or HO
    from_: date = Field(alias="from")
    to: Optional[date] = None


class Person(M):
    id: str
    canonical_name: str
    first_name: str
    last_name: str
    title: Optional[str] = None
    variants: list[str]
    username: str
    home_firm: str
    service_line: str
    roles: list[RoleSpell]
    joined: date
    left: Optional[date] = None
    key: bool = False
    role_hint: Optional[str] = None
    nationality: str = ""
    notes: str = ""


class ClientVariant(M):
    name: str
    firm: str
    from_: date = Field(alias="from")
    to: Optional[date] = None


class Client(M):
    id: str
    canonical_name: str
    variants: list[ClientVariant]
    role: Literal["q3_target", "q3_lookalike", "key", "background"]
    segment: str
    location: Location
    lookalike_of: Optional[str] = None
    notes: str = ""


class Price(M):
    amount: float
    currency: Literal["GBP", "USD", "EUR"]


class ProjectDates(M):
    quote: date
    start: Optional[date] = None
    interim: Optional[date] = None
    completion: Optional[date] = None


PLANTED_PROJECT_TAGS = {
    "q2_correct_B1", "q2_correct_B2", "q2_correct_C1", "q2_correct_C2",
    "q2_distractor_herg_only", "q2_distractor_cyp_other_chemotype", "q2_distractor_right_client_wrong_assay",
    "q3_target_A", "q3_target_C", "q3_target_E", "q3_lookalike",
    "q4_G1", "q4_G2",
    "q5_structbio_D", "q5_structbio_A",
}


class Project(M):
    id: str  # canonical, PRJnnnn
    firm: str
    firm_project_id: str
    lims_id: str
    title: str
    client_id: str
    client_variant: str
    services: list[str]
    assays: list[str]
    series_id: Optional[str] = None
    n_compounds: int = 0
    lead: str
    team: list[str] = []
    dates: ProjectDates
    status: Literal["completed", "in_progress", "lost", "unanswered", "on_hold", "cancelled"]
    price: Price
    turnaround_days: Optional[int] = None  # calendar days, start -> report
    outcome: str = ""
    planted: list[str] = []
    notes: str = ""


class Series(M):
    id: str
    name: str
    chemotype: str
    is_kinase: bool
    target: str
    client_id: Optional[str] = None
    core_smiles: str  # with [*:1], [*:2] attachment points
    r_groups: dict[str, list[str]]  # "1": [smiles fragments with [*:1]]
    compound_prefix: str
    notes: str = ""


# ---------------------------------------------------------------- loading

def _load_yaml(name: str):
    p = WORLD / f"{name}.yaml"
    if not p.exists():
        return None
    return yaml.safe_load(p.read_text()) or {}


class World:
    def __init__(self):
        self.group: Optional[Group] = None
        self.firms: dict[str, Firm] = {}
        self.people: dict[str, Person] = {}
        self.clients: dict[str, Client] = {}
        self.projects: dict[str, Project] = {}
        self.series: dict[str, Series] = {}
        self.assays: dict[str, dict] = {}
        self.service_lines: dict[str, dict] = {}

    # helpers
    def firm_name(self, letter: str) -> str:
        if letter == "HO":
            return self.group.name
        return self.firms[letter].legacy_name

    def unit_end(self, unit: str) -> date:
        return TODAY

    def unit_start(self, unit: str) -> date:
        if unit == "HO":
            return self.group.formed
        return self.firms[unit].founded

    def employed(self, pid: str, unit: Optional[str], on: date) -> bool:
        p = self.people[pid]
        for r in p.roles:
            if (unit is None or r.unit == unit) and r.from_ <= on and (r.to is None or on <= r.to):
                return True
        return False

    def role_at(self, pid: str, on: date) -> Optional[RoleSpell]:
        for r in self.people[pid].roles:
            if r.from_ <= on and (r.to is None or on <= r.to):
                return r
        return None

    def client_variants_for(self, cid: str, firm: str, on: Optional[date] = None) -> list[str]:
        c = self.clients[cid]
        out = []
        for v in c.variants:
            if v.firm == firm and (on is None or (v.from_ <= on and (v.to is None or on <= v.to))):
                out.append(v.name)
        return out

    def all_client_names(self) -> set[str]:
        s = set()
        for c in self.clients.values():
            s.add(c.canonical_name)
            s.update(v.name for v in c.variants)
        return s


def _parse_list(raw, key, model, errors, stage):
    out = {}
    items = raw.get(key, []) if isinstance(raw, dict) else raw
    for i, item in enumerate(items or []):
        try:
            obj = model.model_validate(item)
        except ValidationError as e:
            ident = (item or {}).get("id") or (item or {}).get("letter") or f"#{i}"
            for err in e.errors():
                loc = ".".join(str(x) for x in err["loc"])
                errors.append(f"[{stage}] {key} {ident}: {loc}: {err['msg']}")
            continue
        k = getattr(obj, "id", None) or getattr(obj, "letter")
        if k in out:
            errors.append(f"[{stage}] duplicate {key} id {k}")
        out[k] = obj
    return out


def load_world(errors: Optional[list] = None, upto: Optional[str] = None) -> World:
    errors = errors if errors is not None else []
    w = World()
    a = _load_yaml("assays") or {}
    w.service_lines = {s["id"]: s for s in a.get("service_lines", [])}
    w.assays = {x["id"]: x for x in a.get("assays", [])}
    stages = STAGES if upto is None else STAGES[: STAGES.index(upto) + 1]
    for st in stages:
        raw = _load_yaml(st)
        if raw is None:
            errors.append(f"[{st}] world/{st}.yaml missing")
            continue
        if st == "group":
            try:
                w.group = Group.model_validate(raw.get("group", raw))
            except ValidationError as e:
                for err in e.errors():
                    errors.append(f"[group] {'.'.join(map(str, err['loc']))}: {err['msg']}")
        elif st == "firms":
            w.firms = _parse_list(raw, "firms", Firm, errors, st)
        elif st == "people":
            w.people = _parse_list(raw, "people", Person, errors, st)
        elif st == "clients":
            w.clients = _parse_list(raw, "clients", Client, errors, st)
        elif st == "projects":
            w.projects = _parse_list(raw, "projects", Project, errors, st)
        elif st == "compounds":
            w.series = _parse_list(raw, "series", Series, errors, st)
    return w


@lru_cache(maxsize=1)
def world() -> World:
    errs: list[str] = []
    w = load_world(errs)
    return w


# ---------------------------------------------------------------- validation

def _in(d: Optional[date], lo: date, hi: Optional[date]) -> bool:
    return d is None or (lo <= d and (hi is None or d <= hi))


def validate_world(upto: Optional[str] = None) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings)."""
    errors: list[str] = []
    warns: list[str] = []
    w = load_world(errors, upto)
    stages = STAGES if upto is None else STAGES[: STAGES.index(upto) + 1]
    bl = namecheck.Blocklist.load()

    def name_ok(s: str, ctx: str, person=False):
        hit = bl.check_name(s, person=person)
        if hit:
            errors.append(f"{ctx}: name '{s}' hits blocklist ({hit})")

    # group
    g = w.group
    if g:
        name_ok(g.name, "[group]")
        if g.template.kind != "group":
            errors.append("[group] template.kind must be 'group'")
        if "{firm}" not in g.brand_line_pattern:
            errors.append("[group] brand_line_pattern must contain {firm}")

    # firms
    if "firms" in stages and w.firms:
        if sorted(w.firms) != FIRM_LETTERS:
            errors.append(f"[firms] need exactly firms A-G, got {sorted(w.firms)}")
        for L, f in w.firms.items():
            ctx = f"[firms] {L}"
            name_ok(f.legacy_name, ctx)
            name_ok(f.short_name, ctx)
            if not f.founded < f.joined_group <= TODAY:
                errors.append(f"{ctx}: need founded < joined_group <= {TODAY}")
            if L == "A" and f.role != "founder":
                errors.append(f"{ctx}: A must be role founder")
            if L == "G":
                if f.role != "held_back":
                    errors.append(f"{ctx}: G must be role held_back")
                if not (f.joined_group.year == 2026 and f.joined_group.month >= 9):
                    errors.append(f"{ctx}: G joined_group must be ~October 2026")
            if L not in ("A", "G") and f.role != "acquired":
                errors.append(f"{ctx}: role must be acquired")
            if L in "BCDEF" and not (1996 <= f.joined_group.year <= 2024):
                errors.append(f"{ctx}: acquisitions must fall 1996-2024")
            if g and L == "A" and f.joined_group != g.formed:
                errors.append(f"{ctx}: A.joined_group must equal group.formed ({g.formed})")
            if f.file_era_start < f.founded.year:
                errors.append(f"{ctx}: file_era_start before founded")
            for sl in f.service_lines:
                if sl not in w.service_lines:
                    errors.append(f"{ctx}: unknown service line {sl}")
            kinds = [t.kind for t in sorted(f.templates, key=lambda t: t.from_)]
            if not kinds or kinds[0] != "legacy":
                errors.append(f"{ctx}: first template must be legacy")
            if L != "G" and "group" not in kinds:
                errors.append(f"{ctx}: needs a group-template period after acquisition")
            ts = sorted(f.templates, key=lambda t: t.from_)
            if ts and ts[0].from_ > f.founded.replace(year=max(f.founded.year, f.file_era_start)):
                warns.append(f"{ctx}: first template starts after founding/era start")
            for a, b in zip(ts, ts[1:]):
                if a.to is None or a.to >= b.from_:
                    errors.append(f"{ctx}: template {a.id} must end before {b.id} starts")
            if ts and ts[-1].to is not None:
                errors.append(f"{ctx}: last template must be open-ended (to: null)")
            for t in ts:
                if t.kind == "group" and t.from_ < f.joined_group:
                    errors.append(f"{ctx}: group template {t.id} before acquisition")
                if t.kind == "transition" and t.from_ < f.joined_group:
                    errors.append(f"{ctx}: transition template {t.id} before acquisition")
            try:
                re.compile(f.id_formats.project_id_regex)
                re.compile(f.id_formats.lims_id_regex)
            except re.error as e:
                errors.append(f"{ctx}: bad id regex: {e}")
        acq = sorted((f.joined_group, L) for L, f in w.firms.items())
        if [L for _, L in acq][0] != "A":
            errors.append("[firms] A must be the first (founding) firm")
        # assay variants
        for aid, a in w.assays.items():
            for fl, vs in (a.get("variants") or {}).items():
                if fl not in FIRM_LETTERS:
                    errors.append(f"[firms] assay {aid}: variant key {fl} is not a firm letter")
        for aid, a in w.assays.items():
            for fl, vs in (a.get("variants") or {}).items():
                for v in vs:
                    nm = v if isinstance(v, str) else v.get("name", "")
                    f = w.firms.get(fl)
                    if f and (nm.lower().startswith(f.short_name.lower()) or nm.strip().lower() == a["name"].strip().lower() and fl != "B"):
                        errors.append(f"[firms] assay {aid} variant '{nm}' at {fl}: use the house name staff actually say (no firm-name prefix, not just the canonical name)")
        exs = Counter()
        for L, f in w.firms.items():
            for ex in f.naming_style.filename_examples:
                exs[re.sub(r"[A-Za-z]{1,3}[-_.]?\d{2,4}[-_./]?\d{2,4}", "ID", re.sub(r"\d{4}-\d{2}-\d{2}", "DATE", ex))] += 1
            if len(f.naming_style.filename_examples) < 4:
                errors.append(f"[firms] {L}: give >=4 filename_examples showing this firm's own habits")
        for k, c in exs.items():
            if c > 2:
                errors.append(f"[firms] filename example pattern '{k}' repeated across {c} firms; each firm needs its own naming habits")
        herg_var = set()
        for fl, vs in (w.assays.get("herg", {}).get("variants") or {}).items():
            herg_var.update(v if isinstance(v, str) else v.get("name") for v in vs)
        if len(herg_var) < 3:
            errors.append("[firms] assay herg needs >=3 distinct variant names across firms (e.g. hERG patch clamp / hERG QPatch / IKr inhibition)")
        cyp_var = set()
        for fl, vs in (w.assays.get("cyp_inhib", {}).get("variants") or {}).items():
            cyp_var.update(v if isinstance(v, str) else v.get("name") for v in vs)
        if len(cyp_var) < 2:
            errors.append("[firms] assay cyp_inhib needs >=2 distinct variant names across firms")

    # people
    if "people" in stages and w.people:
        n = len(w.people)
        if not 150 <= n <= 250:
            (errors if upto in (None, "projects", "compounds", "clients") else warns).append(
                f"[people] staff directory has {n} people; need 150-250 (run `mockgen world fill-staff`)")
        users = Counter(p.username for p in w.people.values())
        for u, c in users.items():
            if c > 1:
                errors.append(f"[people] duplicate username {u}")
        for pid, p in w.people.items():
            ctx = f"[people] {pid} {p.canonical_name}"
            name_ok(p.canonical_name, ctx, person=True)
            if p.home_firm not in ORG_UNITS:
                errors.append(f"{ctx}: home_firm {p.home_firm} unknown")
            if p.left and p.left > TODAY:
                errors.append(f"{ctx}: left after today")
            if p.left and p.left < p.joined:
                errors.append(f"{ctx}: left before joined")
            if p.key and len(p.variants) < 3:
                errors.append(f"{ctx}: key staff need >=3 name variants")
            if not p.roles:
                errors.append(f"{ctx}: no roles")
            for r in p.roles:
                if r.unit not in ORG_UNITS:
                    errors.append(f"{ctx}: role unit {r.unit} unknown")
                    continue
                if r.from_ < p.joined or (p.left and (r.to is None or r.to > p.left)):
                    errors.append(f"{ctx}: role '{r.title}' {r.from_}..{r.to} outside employment {p.joined}..{p.left}")
                if w.firms or r.unit == "HO":
                    try:
                        lo = w.unit_start(r.unit)
                    except Exception:
                        lo = None
                    if lo and r.from_ < lo:
                        errors.append(f"{ctx}: role at {r.unit} starts {r.from_} before unit existed ({lo})")
                if r.unit == "HO" and g and r.from_ < g.formed:
                    errors.append(f"{ctx}: HO role before group formed")
                if r.unit == "G" and r.to is None and p.left is None:
                    pass
            if p.left is None and p.roles and p.roles[-1].to is not None:
                errors.append(f"{ctx}: current employee's last role must be open (to: null)")
            for a, b in zip(p.roles, p.roles[1:]):
                if a.to is None or a.to > b.from_:
                    errors.append(f"{ctx}: roles overlap or unordered ({a.title} / {b.title})")
        hints = Counter(p.role_hint for p in w.people.values() if p.role_hint)
        for h in ["leaver_old_laptop", "q2_lead_B_early", "q2_lead_B_recent", "q2_lead_C_early",
                  "q2_lead_C_recent", "bioinf_lead_D", "founder_A", "group_ceo", "integration_director", "tox_lead_G"]:
            if hints.get(h, 0) != 1:
                errors.append(f"[people] need exactly one person with role_hint {h} (found {hints.get(h, 0)})")
        for p in w.people.values():
            if p.role_hint in ("leaver_old_laptop", "q2_lead_C_early") and not p.left:
                errors.append(f"[people] {p.id} ({p.role_hint}) must have left")

    # clients
    if "clients" in stages and w.clients:
        n = len(w.clients)
        if not 60 <= n <= 80:
            errors.append(f"[clients] {n} clients; need 60-80")
        roles = Counter(c.role for c in w.clients.values())
        if roles["q3_target"] != 1 or roles["q3_lookalike"] < 1:
            errors.append("[clients] need exactly 1 q3_target and >=1 q3_lookalike")
        for cid, c in w.clients.items():
            ctx = f"[clients] {cid} {c.canonical_name}"
            name_ok(c.canonical_name, ctx)
            for v in c.variants:
                name_ok(v.name, ctx)
                if v.firm not in ORG_UNITS:
                    errors.append(f"{ctx}: variant firm {v.firm} unknown")
                    continue
                if w.firms and v.firm in w.firms and v.from_ < w.firms[v.firm].founded:
                    errors.append(f"{ctx}: variant '{v.name}' at {v.firm} starts before firm founded")
            if c.role == "q3_target":
                names_by_firm = {}
                for v in c.variants:
                    names_by_firm.setdefault(v.firm, set()).add(v.name)
                for fl in "ACEG":
                    if fl not in names_by_firm:
                        errors.append(f"{ctx}: q3 target needs a variant used at firm {fl}")
                for fl in "DF":
                    if fl in names_by_firm:
                        errors.append(f"{ctx}: q3 target must never be a client of firm {fl}")
                distinct = {v.name for v in c.variants if v.firm in "ACEG"}
                if len(distinct) < 4:
                    errors.append(f"{ctx}: q3 target needs 4 distinct variants across A, C, E, G (has {len(distinct)})")
                g_only = {v.name for v in c.variants if v.firm == "G"} - {v.name for v in c.variants if v.firm != "G"}
                if not g_only:
                    errors.append(f"{ctx}: the 4th variant must be used only at G")
            if c.role == "q3_lookalike" and not c.lookalike_of:
                errors.append(f"{ctx}: lookalike_of required")

    # projects
    if "projects" in stages and w.projects:
        st = Counter(p.status for p in w.projects.values())
        tot = len(w.projects)
        if tot < 80:
            warns.append(f"[projects] only {tot} projects")
        comp = st["completed"] / tot
        if not 0.55 <= comp <= 0.75:
            warns.append(f"[projects] completed share {comp:.0%} (target ~65%)")
        md = Counter((p.dates.quote.month, p.dates.quote.day) for p in w.projects.values())
        for k, c in md.items():
            if c > 3:
                errors.append(f"[projects] {c} projects quoted on month-day {k[0]:02d}-{k[1]:02d}; spread dates realistically across the year")
        stems = Counter(re.sub(r"[\d#]+", "", re.sub(r"\s+[-—–]\s+.*$", "", p.title)).strip().lower() for p in w.projects.values())
        for k, c in stems.items():
            if c > 3:
                errors.append(f"[projects] {c} projects share the title stem '{k}'; write specific titles")
        if any(re.search(r"work package \d+", p.title, re.I) for p in w.projects.values()):
            errors.append("[projects] titles must not use numbered 'work package NN' placeholders")
        oc = Counter(p.outcome.strip() for p in w.projects.values())
        for k, c in oc.items():
            if c > 2:
                errors.append(f"[projects] outcome text repeated on {c} projects: '{k[:60]}'; write a specific outcome per project")
        seqs = Counter()
        for p in w.projects.values():
            m = re.findall(r"\d+", p.firm_project_id)
            if m and int(m[-1]) <= 3:
                seqs[p.firm] += 1
        for fl, c in seqs.items():
            if c > 4:
                errors.append(f"[projects] firm {fl}: {c} project ids with sequence <= 3; sequence numbers should reflect a busy CRO (e.g. 0147), not a per-world counter")
        planted = Counter(t for p in w.projects.values() for t in p.planted)
        for t in PLANTED_PROJECT_TAGS:
            if planted.get(t, 0) != 1:
                errors.append(f"[projects] planted tag {t} must be on exactly one project (found {planted.get(t, 0)})")
        for t in planted:
            if t not in PLANTED_PROJECT_TAGS:
                errors.append(f"[projects] unknown planted tag {t}")
        lims = Counter(p.lims_id for p in w.projects.values())
        fids = Counter(p.firm_project_id for p in w.projects.values())
        for k, c in list(lims.items()) + list(fids.items()):
            if c > 1:
                errors.append(f"[projects] duplicate id {k}")
        for pid, p in w.projects.items():
            ctx = f"[projects] {pid}"
            if p.firm not in w.firms:
                errors.append(f"{ctx}: unknown firm {p.firm}")
                continue
            f = w.firms[p.firm]
            if not re.fullmatch(f.id_formats.project_id_regex, p.firm_project_id):
                errors.append(f"{ctx}: firm_project_id {p.firm_project_id} doesn't match {f.id_formats.project_id_regex}")
            if not re.fullmatch(f.id_formats.lims_id_regex, p.lims_id):
                errors.append(f"{ctx}: lims_id {p.lims_id} doesn't match {f.id_formats.lims_id_regex}")
            if p.client_id not in w.clients:
                errors.append(f"{ctx}: unknown client {p.client_id}")
            else:
                c = w.clients[p.client_id]
                ok_names = w.client_variants_for(p.client_id, p.firm, p.dates.quote)
                if not ok_names and not c.variants:
                    ok_names = [c.canonical_name]
                if p.client_variant not in ok_names:
                    errors.append(f"{ctx}: client_variant '{p.client_variant}' not valid for {p.client_id} at firm {p.firm} on {p.dates.quote} (allowed {ok_names})")
                if c.role == "q3_target" and p.firm in "DF":
                    errors.append(f"{ctx}: q3 target client must never buy from D or F")
            for a in p.assays:
                if a not in w.assays:
                    errors.append(f"{ctx}: unknown assay {a}")
            ds = [p.dates.quote, p.dates.start, p.dates.interim, p.dates.completion]
            seq = [d for d in ds if d]
            if seq != sorted(seq):
                errors.append(f"{ctx}: dates out of order")
            for d in seq:
                if not (max(f.founded, date(f.file_era_start, 1, 1)) <= d <= TODAY):
                    errors.append(f"{ctx}: date {d} outside firm {p.firm} lifetime/era")
            if p.status == "completed" and not (p.dates.start and p.dates.completion):
                errors.append(f"{ctx}: completed needs start and completion")
            if p.status in ("lost", "unanswered") and (p.dates.start or p.dates.completion):
                errors.append(f"{ctx}: lost/unanswered proposals have no start/completion")
            if p.status == "in_progress" and (p.dates.completion or not p.dates.start):
                errors.append(f"{ctx}: in_progress needs start and no completion")
            if p.status == "completed" and p.dates.start and p.dates.completion and p.turnaround_days is not None:
                td = (p.dates.completion - p.dates.start).days
                if td != p.turnaround_days:
                    errors.append(f"{ctx}: turnaround_days {p.turnaround_days} != completion-start {td}")
            if p.lead not in w.people:
                errors.append(f"{ctx}: unknown lead {p.lead}")
            for pp in [p.lead] + p.team:
                if pp not in w.people:
                    errors.append(f"{ctx}: unknown person {pp}")
                    continue
                for d in [p.dates.quote, p.dates.start, p.dates.completion]:
                    if d and not w.employed(pp, p.firm, d):
                        errors.append(f"{ctx}: {pp} not employed at firm {p.firm} on {d}")
            if p.series_id and "compounds" not in stages:
                pass
            # planted constraints
            tags = set(p.planted)
            q2c = {t for t in tags if t.startswith("q2_correct") or t.startswith("q4_G")}
            if q2c:
                if p.status != "completed":
                    errors.append(f"{ctx}: q2/q4 projects must be completed")
                if not {"herg", "cyp_inhib"} <= set(p.assays):
                    errors.append(f"{ctx}: q2/q4 projects need assays herg and cyp_inhib")
                if not 36 <= p.n_compounds <= 44:
                    errors.append(f"{ctx}: q2/q4 projects need ~40 compounds (36-44)")
                if p.turnaround_days is None or p.turnaround_days > 21:
                    errors.append(f"{ctx}: q2/q4 projects need turnaround <= 21 days")
                if not p.series_id:
                    errors.append(f"{ctx}: q2/q4 projects need a kinase series_id")
                want = next(iter(q2c))
                firm_need = {"q2_correct_B1": "B", "q2_correct_B2": "B", "q2_correct_C1": "C", "q2_correct_C2": "C", "q4_G1": "G", "q4_G2": "G"}[want]
                if p.firm != firm_need:
                    errors.append(f"{ctx}: {want} must be at firm {firm_need}")
            if "q2_distractor_herg_only" in tags and ("herg" not in p.assays or any(a.startswith("cyp") for a in p.assays)):
                errors.append(f"{ctx}: herg-only distractor must have herg and no CYP assay")
            if "q2_distractor_cyp_other_chemotype" in tags and "cyp_inhib" not in p.assays:
                errors.append(f"{ctx}: CYP distractor needs cyp_inhib")
            if "q2_distractor_right_client_wrong_assay" in tags and ("herg" in p.assays or "cyp_inhib" in p.assays):
                errors.append(f"{ctx}: right-client-wrong-assay distractor must not include herg/cyp_inhib")
            for t, fl in [("q3_target_A", "A"), ("q3_target_C", "C"), ("q3_target_E", "E")]:
                if t in tags:
                    if p.firm != fl:
                        errors.append(f"{ctx}: {t} must be at firm {fl}")
                    if p.client_id in w.clients and w.clients[p.client_id].role != "q3_target":
                        errors.append(f"{ctx}: {t} must be for the q3 target client")
            if "q3_lookalike" in tags and p.client_id in w.clients and w.clients[p.client_id].role != "q3_lookalike":
                errors.append(f"{ctx}: q3_lookalike project must be for the lookalike client")
            if "q5_structbio_D" in tags and p.firm != "D":
                errors.append(f"{ctx}: q5_structbio_D must be at firm D")
            if "q5_structbio_A" in tags and p.firm != "A":
                errors.append(f"{ctx}: q5_structbio_A must be at firm A")
            blob = (p.title + " " + p.outcome + " " + p.notes).lower()
            if "cryo" in blob:
                errors.append(f"{ctx}: no cryo-EM content anywhere")
        # q2 cross-project constraints
        q2 = [p for p in w.projects.values() if any(t.startswith("q2_correct") for t in p.planted)]
        years = [p.dates.start.year for p in q2 if p.dates.start]
        if len(set(years)) != len(years):
            errors.append("[projects] q2 correct projects must be from different years")
        rc = [p for p in w.projects.values() if "q2_distractor_right_client_wrong_assay" in p.planted]
        if rc and q2 and rc[0].client_id not in {p.client_id for p in q2}:
            errors.append("[projects] right-client-wrong-assay distractor must share a client with a q2 correct project")
        g4 = [p for p in w.projects.values() if any(t.startswith("q4_G") for t in p.planted)]
        tgt = [c for c in w.clients.values() if c.role == "q3_target"]
        if tgt and g4 and not any(p.client_id == tgt[0].id for p in g4):
            errors.append("[projects] at least one q4_G project must be for the q3 target client (4th variant)")
        # q3 target never at D/F handled above; must have A, C, E projects
        if tgt:
            firms_bought = {p.firm for p in w.projects.values() if p.client_id == tgt[0].id}
            for fl in "ACE":
                if fl not in firms_bought:
                    errors.append(f"[projects] q3 target has no project at {fl}")

    # compounds
    if "compounds" in stages and w.series:
        from . import chem
        for sid, s in w.series.items():
            ctx = f"[compounds] {sid}"
            try:
                import statistics
                from rdkit import Chem
                prods = chem.enumerate_series(s)
                if prods:
                    mw = statistics.median(p["mw"] for p in prods)
                    rings = statistics.median(Chem.MolFromSmiles(p["smiles"]).GetRingInfo().NumRings() for p in prods)
                    if not (300 <= mw <= 560) or rings < 3:
                        errors.append(f"{ctx}: enumerated compounds not drug-like enough (median MW {mw:.0f}, median rings {rings}); want MW 300-560 and >=3 rings")
            except Exception as e:
                errors.append(f"{ctx}: enumeration failed: {e}")
            if any(len(v) < 8 for v in s.r_groups.values()):
                errors.append(f"{ctx}: each attachment point needs >=8 fragments")
            errs = chem.check_series(s)
            errors.extend(f"{ctx}: {e}" for e in errs)
        for pid, p in w.projects.items():
            if p.series_id and p.series_id not in w.series:
                errors.append(f"[compounds] project {pid} references unknown series {p.series_id}")
            if p.series_id and p.series_id in w.series:
                cap = chem.series_capacity(w.series[p.series_id])
                if p.n_compounds > cap:
                    errors.append(f"[compounds] project {pid} needs {p.n_compounds} compounds but series {p.series_id} enumerates only {cap}")
                tags = set(p.planted)
                if tags & {"q2_correct_B1", "q2_correct_B2", "q2_correct_C1", "q2_correct_C2", "q4_G1", "q4_G2"} and not w.series[p.series_id].is_kinase:
                    errors.append(f"[compounds] q2/q4 project {pid} needs a kinase series")
                if "q2_distractor_cyp_other_chemotype" in tags and w.series[p.series_id].is_kinase:
                    errors.append(f"[compounds] CYP distractor {pid} must use a non-kinase series")
        for pid, p in w.projects.items():
            needs = set(p.assays) & {"herg", "cyp_inhib", "cyp_ic50", "kinase_primary", "kinase_panel", "mic_stab", "hep_stab", "ppb", "caco2", "solubility", "cytotox", "ames", "micronucleus"}
            if needs and not p.series_id:
                errors.append(f"[compounds] project {pid} runs compound assays {sorted(needs)} but has no series_id")
            if needs and p.n_compounds < 1:
                errors.append(f"[compounds] project {pid} runs compound assays but n_compounds is 0")
    return errors, warns
