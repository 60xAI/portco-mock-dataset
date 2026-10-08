"""Manifest (file list): schema, merge, validation, planted coverage."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, datetime
from functools import lru_cache
from typing import Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError

from .paths import MANIFEST, TODAY
from .world import load_world, ORG_UNITS

CAP = 350
UNITS = ["A", "B", "C", "D", "E", "F", "G", "HO"]

DOC_TYPES = {
    "deck_capability", "deck_pitch", "deck_readout", "deck_training", "deck_internal",
    "wb_results", "wb_tracker", "wb_pricelist", "wb_other",
    "report_study", "report_client",
    "word_proposal", "word_sop", "word_sow", "word_memo",
    "service_catalogue", "lims_export", "staff_directory", "client_list",
    "board_pack", "integration_doc", "junk",
}
FORMATS = {"pptx", "ppt", "xlsx", "xls", "docx", "doc", "pdf", "csv"}
FINISH = {"final", "draft", "interim", "superseded", "abandoned", "empty_template"}
MESS = {"copy_of", "version_suffix", "unhelpful_name", "duplicate_across_firms", "typo", "tracked_changes", "comments",
        "tbc_placeholders", "mixed_units", "inconsistent_dates", "leaver_folder", "half_filled", "stale_template", "draft_mark",
        "empty_sections", "near_empty"}
TIERS = {"sol", "haiku", "haiku_low", "orchestrator", "script"}
RELS = {"version_of", "export_of", "proposal_for", "report_for", "copy_of", "duplicate_of", "source_of", "results_for", "related"}

# format quotas (total incl. planted); junk, catalogues and csv counted separately
QUOTA = {
    "A": dict(deck=13, wb=10, pdf=15, word=8, catalogue=1, junk=3, csv=0, ppt=3, xls=3, doc=2, scan=3, export=1),
    "B": dict(deck=14, wb=15, pdf=19, word=7, catalogue=1, junk=3, csv=0, ppt=2, xls=3, doc=1, scan=3, export=2),
    "C": dict(deck=13, wb=14, pdf=17, word=6, catalogue=1, junk=3, csv=0, ppt=1, xls=2, doc=1, scan=2, export=2),
    "D": dict(deck=13, wb=6, pdf=9, word=4, catalogue=1, junk=2, csv=0, ppt=1, xls=0, doc=0, scan=1, export=3),
    "E": dict(deck=10, wb=14, pdf=16, word=6, catalogue=1, junk=3, csv=0, ppt=1, xls=2, doc=0, scan=3, export=1),
    "F": dict(deck=7, wb=8, pdf=10, word=5, catalogue=1, junk=2, csv=0, ppt=0, xls=0, doc=0, scan=1, export=1),
    "G": dict(deck=6, wb=9, pdf=12, word=4, catalogue=1, junk=2, csv=0, ppt=0, xls=0, doc=0, scan=2, export=1),
    "HO": dict(deck=6, wb=6, pdf=4, word=4, catalogue=0, junk=2, csv=3, ppt=0, xls=0, doc=0, scan=0, export=1),
}


class M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Rel(M):
    id: str
    rel: str


class Entry(M):
    id: str
    unit: str
    root: Literal["archive", "heldback"]
    path: str
    filename: str
    format: str
    doc_type: str
    pdf_kind: Optional[Literal["native", "scan", "export"]] = None
    year: int
    era: Literal["legacy", "transition", "group"]
    template: str
    created: datetime
    modified: datetime
    author: str
    last_saved_by: str
    projects: list[str] = []
    client_id: Optional[str] = None
    client_variant: Optional[str] = None
    finish: str
    mess: list[str] = []
    planted: list[str] = []
    related: list[Rel] = []
    tier: str
    target_length: str
    summary: str
    pilot: bool = False


def family(e: Entry) -> str:
    """Content family the writer produces."""
    if e.format == "csv":
        return "csv"
    if e.pdf_kind == "export":
        return "export"
    if e.pdf_kind == "scan":
        return "scan"
    if e.format in ("pptx", "ppt"):
        return "deck"
    if e.format in ("xlsx", "xls"):
        return "workbook"
    return "document"


def quota_bucket(e: Entry) -> str:
    if e.doc_type == "junk":
        return "junk"
    if e.doc_type == "service_catalogue":
        return "catalogue"
    if e.format == "csv":
        return "csv"
    return {"pptx": "deck", "ppt": "deck", "xlsx": "wb", "xls": "wb", "pdf": "pdf", "docx": "word", "doc": "word"}[e.format]


def _load_file(p, errors) -> list[Entry]:
    raw = yaml.safe_load(p.read_text()) or {}
    items = raw.get("files", []) if isinstance(raw, dict) else raw
    out = []
    for i, it in enumerate(items or []):
        try:
            out.append(Entry.model_validate(it))
        except ValidationError as e:
            ident = (it or {}).get("id", f"#{i}")
            for err in e.errors():
                errors.append(f"[{p.name}] {ident}: {'.'.join(map(str, err['loc']))}: {err['msg']}")
    return out


def load_entries(errors: Optional[list] = None) -> list[Entry]:
    errors = errors if errors is not None else []
    out = []
    for u in UNITS:
        p = MANIFEST / f"{u}.yaml"
        if p.exists():
            out.extend(_load_file(p, errors))
    return out


@lru_cache(maxsize=1)
def entries_by_id() -> dict[str, Entry]:
    return {e.id: e for e in load_entries([])}


def full_path(e: Entry) -> str:
    return f"{e.path.rstrip('/')}/{e.filename}"


# ---------------------------------------------------------------- planted

def load_planted() -> list[dict]:
    p = MANIFEST / "planted.yaml"
    if not p.exists():
        return []
    return (yaml.safe_load(p.read_text()) or {}).get("planted", [])


def planted_for(unit: Optional[str]) -> str:
    items = [x for x in load_planted() if unit is None or x["entry"]["unit"] == unit]
    return yaml.safe_dump({"planted": items}, sort_keys=False, allow_unicode=True, width=120)


# ---------------------------------------------------------------- validation

def validate_manifest(unit: Optional[str] = None) -> tuple[list[str], list[str]]:
    """unit=None validates the whole archive; unit='B' validates one unit's file (for parallel agents)."""
    errors: list[str] = []
    warns: list[str] = []
    werr: list[str] = []
    w = load_world(werr)
    if werr:
        errors.append(f"world has {len(werr)} load errors; fix world first")
        return errors, warns
    all_es = load_entries(errors)
    if unit:
        es = [e for e in all_es if e.unit == unit]
        if not (MANIFEST / f"{unit}.yaml").exists():
            errors.append(f"manifest/{unit}.yaml missing")
        planted_stub = {x["entry"]["id"] for x in load_planted()}
    else:
        es = all_es
        planted_stub = set()
        for u in UNITS:
            if not (MANIFEST / f"{u}.yaml").exists():
                errors.append(f"manifest/{u}.yaml missing")
        if len(es) > CAP:
            errors.append(f"archive has {len(es)} files; cap is {CAP}")
    ids = Counter(e.id for e in es)
    for k, c in ids.items():
        if c > 1:
            errors.append(f"duplicate file id {k}")
    paths = Counter((e.root, full_path(e).lower()) for e in es)
    for k, c in paths.items():
        if c > 1:
            errors.append(f"duplicate path {k[1]}")
    byid = {e.id: e for e in (all_es if unit else es)}
    shares = {L: f.share_root for L, f in w.firms.items()}
    shares["HO"] = w.group.share_root
    for e in es:
        ctx = f"{e.id} ({e.unit}) {full_path(e)}"
        if e.unit not in UNITS:
            errors.append(f"{ctx}: unknown unit")
            continue
        if e.format not in FORMATS:
            errors.append(f"{ctx}: bad format {e.format}")
        if e.doc_type not in DOC_TYPES:
            errors.append(f"{ctx}: bad doc_type {e.doc_type}")
        if e.finish not in FINISH:
            errors.append(f"{ctx}: bad finish {e.finish}")
        for m in e.mess:
            if m not in MESS:
                errors.append(f"{ctx}: unknown mess flag {m}")
        if e.tier not in TIERS:
            errors.append(f"{ctx}: bad tier {e.tier}")
        for r in e.related:
            if r.rel not in RELS:
                errors.append(f"{ctx}: bad related.rel {r.rel}")
            if r.id not in byid and r.id not in planted_stub:
                errors.append(f"{ctx}: related id {r.id} not in manifest (use ids from your own unit or planted ids)")
        ext = e.filename.rsplit(".", 1)[-1].lower() if "." in e.filename else ""
        if ext != e.format:
            errors.append(f"{ctx}: filename extension .{ext} != format {e.format}")
        if (e.format == "pdf") != (e.pdf_kind is not None):
            errors.append(f"{ctx}: pdf_kind required for pdf (native|scan|export) and only for pdf")
        if e.pdf_kind == "export":
            src = [r.id for r in e.related if r.rel == "export_of"]
            if len(src) != 1:
                errors.append(f"{ctx}: export needs exactly one related export_of (the source deck/doc)")
            elif src[0] in byid and byid[src[0]].format not in ("pptx", "ppt", "docx", "doc", "xlsx"):
                errors.append(f"{ctx}: export_of must point at an Office file")
            if e.tier != "script":
                errors.append(f"{ctx}: exports are rendered by script (tier: script)")
        if e.format == "csv" and e.tier != "script":
            errors.append(f"{ctx}: csv files are generated by script (tier: script)")
        if e.pdf_kind == "scan" and e.planted:
            errors.append(f"{ctx}: scans never carry planted answers")
        want_root = "heldback" if e.unit == "G" else "archive"
        if e.root != want_root:
            errors.append(f"{ctx}: root must be {want_root}")
        segs = [s for s in e.path.split("/") if s]
        if not segs:
            errors.append(f"{ctx}: empty path")
            continue
        if segs[0] not in (shares.get(e.unit), "Archive") and not (e.unit == "G" and segs[0] in (shares["G"],)):
            errors.append(f"{ctx}: path must start with the unit's share root '{shares.get(e.unit)}' or 'Archive'")
        if segs[0] == "Archive" and e.unit == "G":
            errors.append(f"{ctx}: G files stay under G's own share root")
        if not 2 <= len(segs) <= 7:
            errors.append(f"{ctx}: folder depth {len(segs)} outside 2-7")
        elif len(segs) < 3 and e.doc_type not in ("junk", "lims_export", "staff_directory", "client_list"):
            warns.append(f"{ctx}: shallow folder depth {len(segs)}")
        if any(re.search(r'[<>:"\\|?*]', s) for s in segs + [e.filename]):
            errors.append(f"{ctx}: illegal path character")
        if not e.created <= e.modified <= datetime.combine(TODAY, datetime.min.time()).replace(hour=23):
            errors.append(f"{ctx}: need created <= modified <= today")
        if e.year != e.created.year and e.year != e.modified.year:
            errors.append(f"{ctx}: year {e.year} matches neither created nor modified")
        # unit lifetime / era
        if e.unit == "HO":
            lo = w.group.formed
            temps = {w.group.template.id: w.group.template}
        else:
            f = w.firms[e.unit]
            lo = max(f.founded, date(f.file_era_start, 1, 1))
            temps = {t.id: t for t in f.templates}
            temps[w.group.template.id] = w.group.template
        if e.created.date() < lo:
            errors.append(f"{ctx}: created {e.created.date()} before unit's era start {lo}")
        if e.template not in temps:
            errors.append(f"{ctx}: template {e.template} not one of {sorted(temps)}")
        else:
            t = temps[e.template]
            d = e.created.date()
            if not (t.from_ <= d and (t.to is None or d <= t.to)) and "stale_template" not in e.mess:
                errors.append(f"{ctx}: template {t.id} ({t.from_}..{t.to}) not current on created date {d} (add mess flag stale_template if deliberate)")
            if e.era != t.kind:
                errors.append(f"{ctx}: era {e.era} != template kind {t.kind}")
        # people
        for role, pid, d in (("author", e.author, e.created.date()), ("last_saved_by", e.last_saved_by, e.modified.date())):
            if pid not in w.people:
                errors.append(f"{ctx}: {role} {pid} not in world")
                continue
            ok = w.employed(pid, None, d)
            if not ok:
                p = w.people[pid]
                errors.append(f"{ctx}: {role} {pid} {p.canonical_name} not employed on {d} (employed {p.joined}..{p.left})")
        # projects / clients
        for pj in e.projects:
            if pj not in w.projects:
                errors.append(f"{ctx}: unknown project {pj}")
                continue
            p = w.projects[pj]
            if e.unit not in ("HO",) and p.firm != e.unit and "duplicate_across_firms" not in e.mess and segs[0] != "Archive":
                errors.append(f"{ctx}: project {pj} belongs to firm {p.firm}")
            if e.created.date() < p.dates.quote.replace(day=1) and e.doc_type not in ("junk",):
                errors.append(f"{ctx}: created before project {pj} was quoted ({p.dates.quote})")
            if p.status in ("lost", "unanswered") and e.doc_type in ("report_study", "report_client", "wb_results", "deck_readout"):
                errors.append(f"{ctx}: project {pj} is {p.status}; it has only a proposal/quote")
            if p.status == "in_progress" and e.doc_type in ("report_study", "report_client") and e.finish == "final":
                errors.append(f"{ctx}: project {pj} is in progress; no final report yet")
            if p.status in ("on_hold", "cancelled") and e.finish == "final" and e.doc_type in ("report_study", "report_client"):
                errors.append(f"{ctx}: project {pj} is {p.status}; report cannot be final")
        if e.client_id:
            if e.client_id not in w.clients:
                errors.append(f"{ctx}: unknown client {e.client_id}")
            elif e.client_variant:
                c = w.clients[e.client_id]
                allowed = {v.name for v in c.variants} | {c.canonical_name}
                if e.client_variant not in allowed:
                    errors.append(f"{ctx}: client_variant '{e.client_variant}' not a known name of {e.client_id}")
                elif e.unit != "HO":
                    at = w.client_variants_for(e.client_id, e.unit, e.created.date())
                    if at and e.client_variant not in at:
                        errors.append(f"{ctx}: client_variant '{e.client_variant}' not used by firm {e.unit} on {e.created.date()} (used: {at})")
        if re.search(r"cryo[\s-]*(em\b|electron|microscop)", (e.summary + e.filename + e.path), re.I):
            errors.append(f"{ctx}: no cryo-EM content anywhere")

    # quotas (warnings unless grossly off)
    per = defaultdict(Counter)
    for e in es:
        per[e.unit][quota_bucket(e)] += 1
        if e.format in ("ppt", "xls", "doc"):
            per[e.unit][e.format] += 1
        if e.pdf_kind in ("scan", "export"):
            per[e.unit][e.pdf_kind] += 1
    for u in UNITS:
        if not (MANIFEST / f"{u}.yaml").exists() or (unit and u != unit):
            continue
        q = QUOTA[u]
        for k, v in q.items():
            got = per[u][k]
            if abs(got - v) > max(2, round(v * 0.25)):
                errors.append(f"[{u}] {k}: {got} files, quota {v} (allowed ±{max(2, round(v * 0.25))})")
            elif got != v:
                warns.append(f"[{u}] {k}: {got} files, quota {v}")
    # planted coverage
    pl = load_planted()
    for item in pl:
        if unit and item["entry"]["unit"] != unit:
            continue
        pe = item["entry"]
        if pe["id"] not in byid:
            errors.append(f"planted file {pe['id']} ({item.get('label', '')}) missing from manifest/{pe['unit']}.yaml")
            continue
        e = byid[pe["id"]]
        for k in ("unit", "format", "doc_type", "pdf_kind", "tier", "finish", "template", "author", "client_variant"):
            if k in pe and pe[k] is not None and getattr(e, k) != pe[k]:
                errors.append(f"planted {e.id}: field {k} = {getattr(e, k)!r}, must stay {pe[k]!r}")
        if set(pe.get("planted", [])) != set(e.planted):
            errors.append(f"planted {e.id}: planted tags changed")
        if sorted(pe.get("projects", [])) != sorted(e.projects):
            errors.append(f"planted {e.id}: projects changed")
    plant_ids = {x["entry"]["id"] for x in pl}
    for e in es:
        if e.planted and e.id not in plant_ids:
            errors.append(f"{e.id}: only entries from manifest/planted.yaml may carry planted tags")
    # leavers folders exist
    if not unit and not any(e.path.startswith("Archive/Users/") for e in es):
        errors.append("no leavers' folders (Archive/Users/<username>_old_laptop/...) in the manifest")
    return errors, warns


def tree(unit: Optional[str] = None) -> str:
    es = [e for e in load_entries([]) if unit is None or e.unit == unit]
    t: dict = {}
    for e in sorted(es, key=lambda e: (e.root, full_path(e).lower())):
        node = t.setdefault(e.root, {})
        for s in e.path.split("/"):
            if s:
                node = node.setdefault(s + "/", {})
        node[e.filename] = None
    lines = []

    def walk(n, ind):
        for k in n:
            lines.append("  " * ind + k)
            if isinstance(n[k], dict):
                walk(n[k], ind + 1)
    walk(t, 0)
    return "\n".join(lines)


def merge() -> str:
    es = load_entries([])
    out = [e.model_dump(mode="json") for e in es]
    (MANIFEST / "manifest.yaml").write_text(yaml.safe_dump({"files": out}, sort_keys=False, allow_unicode=True, width=140))
    return f"merged {len(es)} entries -> manifest/manifest.yaml"
