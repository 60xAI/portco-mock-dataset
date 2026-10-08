"""`mockgen submit`: validate content JSON, render, reopen, accept or reject with numbered reasons."""
from __future__ import annotations

import json
import re
import shutil
from datetime import timedelta
from pathlib import Path

from pydantic import ValidationError

from . import manifest as Mf
from . import state
from .names import Blocklist
from .paths import CONTENT, TODAY
from .render import PH, numbers, out_path, render_entry, resolve_text, get_table
from .schemas import FAMILY_MODELS
from .textscan import COMMON, COMPANY_RE, DR_RE, FULLNAME_RE, all_text, faker_first_names, find_dates, norm, strings
from .world import load_world


def registry(w):
    orgs = {w.group.name, w.group.short_name, w.group.legal_name}
    for f in w.firms.values():
        orgs |= {f.legacy_name, f.short_name}
    for c in w.clients.values():
        orgs.add(c.canonical_name)
        orgs |= {v.name for v in c.variants}
    org_tokens = set()
    for o in orgs:
        for t in re.findall(r"[A-Za-z][A-Za-z'\-]+", o):
            org_tokens.add(t.lower())
    surnames, fulls, firsts = set(), set(), set()
    for p in w.people.values():
        surnames.add(p.last_name.lower())
        for part in re.split(r"[\s\-]", p.last_name):
            surnames.add(part.lower())
        fulls.add(p.canonical_name.lower())
        fulls.add(f"{p.first_name} {p.last_name}".lower())
        firsts.add(p.first_name)
    return orgs, org_tokens, surnames, fulls, firsts


def person_by_name(w, name: str):
    n = norm(name)
    n2 = re.sub(r"^(dr|prof|professor)\.?\s+", "", n)
    for p in w.people.values():
        cands = {norm(p.canonical_name), norm(f"{p.first_name} {p.last_name}")} | {norm(v) for v in p.variants}
        if n in cands or n2 in cands:
            return p
    for p in w.people.values():
        if n2.endswith(p.last_name.lower()) and n2[:1] == p.first_name[:1].lower():
            return p
    return None


def _table_refs(obj, acc):
    if isinstance(obj, dict):
        if "table_ref" in obj and isinstance(obj["table_ref"], str):
            acc.append(obj["table_ref"])
        for v in obj.values():
            _table_refs(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _table_refs(v, acc)
    return acc


def location_texts(fam: str, raw: dict) -> dict:
    """Map location -> text (resolved) for planted fact checks."""
    out = {}
    if fam == "deck":
        for i, s in enumerate(raw.get("slides", []), 1):
            out[("slide", i)] = norm(resolve_text(all_text(s)))
    elif fam == "workbook":
        for s in raw.get("sheets", []):
            txt = all_text(s)
            for r in _table_refs(s, []):
                t = get_table(r)
                if t:
                    txt += "\n" + "\n".join(" ".join(map(str, row)) for row in [t["columns"]] + t["rows"])
            for row in s.get("rows", []):
                for c in row:
                    if isinstance(c, dict) and c.get("ref"):
                        pid, key = c["ref"].split(":", 1)
                        try:
                            txt += " " + str(numbers(pid)["values"].get(key, ""))
                        except KeyError:
                            pass
            out[("sheet", s.get("name", ""))] = norm(resolve_text(txt))
    else:
        doc = raw.get("document", raw)
        txt = all_text(doc)
        for r in _table_refs(doc, []):
            t = get_table(r)
            if t:
                txt += "\n" + "\n".join(" ".join(map(str, row)) for row in [t["columns"]] + t["rows"])
        out[("doc", 0)] = norm(resolve_text(txt))
    return out


def check_facts(entry, fam, raw, facts, w) -> list[str]:
    errs = []
    locs = location_texts(fam, raw)
    refs = set(_table_refs(raw, []))
    for s in raw.get("sheets", []) if fam == "workbook" else []:
        for d in s.get("data_refs", []):
            refs.add(d.get("table_ref"))

    def where_texts(where):
        if not where:
            return list(locs.values())
        if "slide" in where:
            if where["slide"] == "any":
                return [v for k, v in locs.items() if k[0] == "slide"]
            return [locs.get(("slide", where["slide"]), "")]
        if "sheet" in where:
            if where["sheet"] == "any":
                return [v for k, v in locs.items() if k[0] == "sheet"]
            return [locs.get(("sheet", where["sheet"]), "")]
        return list(locs.values())

    for f in facts:
        where = f.get("where")
        wt = where_texts(where)
        place = f" on {list(where.items())[0][0]} {list(where.items())[0][1]}" if where else ""
        if "text" in f:
            t = norm(resolve_text(f["text"]))
            if not any(t in x for x in wt):
                errs.append(f"required fact missing{place}: '{resolve_text(f['text'])}'")
        if "any_of" in f:
            if not any(norm(a) in x for a in f["any_of"] for x in wt):
                errs.append(f"required fact missing{place}: one of {f['any_of']}")
        if "table_ref" in f:
            ok = f["table_ref"] in refs
            if ok and where and "sheet" in where and where["sheet"] != "any":
                ok = any(d.get("table_ref") == f["table_ref"] for s in raw.get("sheets", []) if s.get("name") == where["sheet"] for d in s.get("data_refs", []))
            if not ok:
                errs.append(f"required table missing: embed {{\"table_ref\": \"{f['table_ref']}\"}} (as a table block / slide table / sheet data_refs entry)")
        if f.get("kind") == "price":
            p = w.projects[f["project"]]
            amt = f"{p.price.amount:,.0f}"
            sym = {"GBP": "£", "USD": "$", "EUR": "€"}[p.price.currency]
            alts = [f"{sym}{amt}", f"{p.price.currency} {amt}", f"{sym} {amt}", f"{sym}{amt.replace(',', '')}", f"{p.price.currency} {amt.replace(',', '')}",
                    f"{p.price.currency}{amt}", f"{amt} {p.price.currency}"]
            if not any(norm(a) in x for a in alts for x in wt) and not any("{{%s:price}}" % p.id in s for s in strings(raw)):
                errs.append(f"required fact missing: the project price {sym}{amt} (or write {{{{{p.id}:price}}}})")
    return errs


def content_checks(entry, fam, raw, w) -> list[str]:
    errs: list[str] = []
    txt_raw = all_text(raw)
    resolve_errs: list[str] = []
    txt = resolve_text(txt_raw, resolve_errs)
    errs += sorted(set(resolve_errs))
    # placeholders/table refs must belong to this file's projects
    used = {m.group(1) for m in PH.finditer(txt_raw)} | {r.split(":")[0] for r in _table_refs(raw, [])}
    for s in raw.get("sheets", []) if fam == "workbook" else []:
        for d in s.get("data_refs", []):
            used.add(str(d.get("table_ref", "")).split(":")[0])
            if not get_table(d.get("table_ref", "")):
                errs.append(f"sheet {s.get('name')}: unknown data_refs table_ref {d.get('table_ref')}")
    for pid in used:
        if pid and pid not in entry.projects and entry.unit != "HO":
            errs.append(f"uses numbers from {pid}, which is not one of this file's projects {entry.projects}")
    for r in _table_refs(raw, []):
        if not get_table(r):
            errs.append(f"unknown table_ref {r}")
    # blocklist
    bl = Blocklist.load()
    hits = bl.scan_text(txt)
    if hits:
        errs.append(f"blocklisted real names: {', '.join(hits)}")
    if re.search(r"cryo", txt, re.I):
        errs.append("mentions cryo-EM/cryo-: the archive must contain no cryo-EM content")
    # unregistered organisations
    orgs, org_tokens, surnames, fulls, firsts = registry(w)
    bad_orgs = set()
    for m in COMPANY_RE.finditer(txt):
        words = re.findall(r"[A-Za-z][A-Za-z'\-]+", m.group(0))
        distinct = [x for x in words[:-1] if x.lower() not in COMMON]
        if not distinct:
            continue
        if not any(x.lower() in org_tokens for x in distinct):
            bad_orgs.add(m.group(0))
    if bad_orgs:
        errs.append(f"unregistered organisation names (use only world names; no invented companies/vendors): {', '.join(sorted(bad_orgs)[:8])}")
    # unregistered people
    bad_people = set()
    for m in DR_RE.finditer(txt):
        if m.group(1).lower() not in surnames:
            bad_people.add(m.group(0))
    fn = faker_first_names() | firsts
    for m in FULLNAME_RE.finditer(txt):
        first, last = m.group(1), m.group(2)
        if first in fn and last.lower() not in COMMON and f"{first} {last}".lower() not in fulls and last.lower() not in org_tokens:
            if last.lower() not in surnames or not any(f.lower() == f"{first} {last}".lower() for f in fulls):
                bad_people.add(f"{first} {last}")
    if bad_people:
        errs.append(f"unregistered person names (use only people from the pack): {', '.join(sorted(bad_people)[:8])}")
    # anachronisms: people who joined after the file; client names before they existed
    mod = entry.modified.date()
    for p in w.people.values():
        if p.joined > mod + timedelta(days=30):
            for v in {p.canonical_name, f"{p.first_name} {p.last_name}"} | {x for x in p.variants if " " in x}:
                if v and re.search(r"\b" + re.escape(v) + r"\b", txt):
                    errs.append(f"names {v}, who joined on {p.joined}, after this file was last saved ({mod})")
                    break
    first_seen = {}
    for c in w.clients.values():
        for v in c.variants:
            first_seen[v.name] = min(first_seen.get(v.name, v.from_), v.from_)
    for name, d0 in first_seen.items():
        if d0 > mod + timedelta(days=60) and re.search(r"\b" + re.escape(name) + r"(?![\w(])", txt):
            errs.append(f"client name '{name}' was not in use until {d0}, after this file ({mod})")
    q3 = next((c for c in w.clients.values() if c.role == "q3_target"), None)
    if q3 and entry.unit != "G":
        g_only = {v.name for v in q3.variants if v.firm == "G"} - {v.name for v in q3.variants if v.firm != "G"}
        for n in g_only:
            if n in txt:
                errs.append(f"'{n}' is only known to the held-back firm G; it must not appear outside G's archive")
    if q3 and entry.unit in ("D", "F"):
        for v in q3.variants:
            if re.search(r"\b" + re.escape(v.name) + r"(?![\w])", txt):
                errs.append(f"{q3.canonical_name} has never been a client of firm {entry.unit}; don't mention it here")
                break
    # group brand did not exist before the group template launched
    gstart = w.group.template.from_
    if mod < gstart and re.search(re.escape(w.group.short_name), txt):
        errs.append(f"mentions '{w.group.short_name}', but the group brand only launched on {gstart}; before that the group was informally 'the Vellacombe group'")
    # dates
    us = entry.unit in w.firms and w.firms[entry.unit].date_convention == "US"
    lo = w.group.formed if entry.unit == "HO" else w.firms[entry.unit].founded
    for raw_d, d in find_dates(txt, us):
        if d > min(TODAY + timedelta(days=365), mod + timedelta(days=400)):
            errs.append(f"date {raw_d} is implausibly far after the file was last saved ({mod})")
        elif d < lo.replace(year=lo.year - 5):
            errs.append(f"date {raw_d} is before the firm existed ({lo})")
    # signature block people must be employed on the signing date
    doc = raw.get("document", raw) if fam in ("document", "scan") else None
    if doc:
        for sg in doc.get("signature_block", []) or []:
            p = person_by_name(w, sg.get("name", ""))
            if not p:
                errs.append(f"signature block name '{sg.get('name')}' is not a person in the world")
                continue
            ds = find_dates(sg.get("date") or "", us)
            on = ds[0][1] if ds else entry.created.date()
            if not w.employed(p.id, None, on):
                errs.append(f"signature block: {p.canonical_name} was not employed on {on} (employed {p.joined}..{p.left})")
    # numbers: compound counts and prices
    projs = [w.projects[p] for p in entry.projects if p in w.projects]
    ncs = {p.n_compounds for p in projs if p.n_compounds}
    if len(ncs) == 1:
        n = next(iter(ncs))
        for m in re.finditer(r"\b(\d{2})\s+(?:test\s+)?(?:compounds|analogues|analogs|test articles|cpds)\b", txt):
            k = int(m.group(1))
            if 25 <= k <= 60 and k != n:
                errs.append(f"says '{m.group(0)}' but the project has {n} compounds")
                break
    return errs


def reopen(path: Path, fmt: str, pdf_kind: str | None) -> str | None:
    try:
        if fmt == "pptx":
            from pptx import Presentation
            Presentation(path)
        elif fmt == "xlsx":
            import openpyxl
            openpyxl.load_workbook(path)
        elif fmt == "docx":
            import docx
            docx.Document(path)
        elif fmt == "pdf":
            from pypdf import PdfReader
            r = PdfReader(str(path))
            n = len(r.pages)
            if n == 0:
                return "PDF has no pages"
            if pdf_kind == "scan":
                t = "".join((pg.extract_text() or "") for pg in r.pages).strip()
                if t:
                    return "scan has a text layer"
                from .archive import ocr_words
                wc = ocr_words(path)
                if wc < 25:
                    return f"Tesseract recovered only {wc} words from the scan"
        elif fmt in ("ppt", "xls", "doc"):
            with open(path, "rb") as fh:
                if fh.read(8) != bytes.fromhex("D0CF11E0A1B11AE1"):
                    return "legacy file is not an OLE2 binary"
        elif fmt == "csv":
            path.read_text(encoding="utf-8-sig")
    except Exception as e:
        return f"rendered file does not reopen: {e}"
    return None


def submit(file_id: str, content_path: str, force: bool = False) -> tuple[bool, str]:
    es = {e.id: e for e in Mf.load_entries([])}
    if file_id not in es:
        return False, f"REJECTED {file_id}\n1. unknown file id"
    if len(es) > Mf.CAP:
        return False, f"REJECTED {file_id}\n1. manifest has {len(es)} files; cap is {Mf.CAP}"
    entry = es[file_id]
    fam = Mf.family(entry)
    if fam not in FAMILY_MODELS:
        return False, f"REJECTED {file_id}\n1. {fam} files are generated by script, not submitted"
    errs: list[str] = []
    try:
        raw = json.loads(Path(content_path).read_text())
    except Exception as e:
        return _reject(file_id, [f"content is not valid JSON: {e}"])
    if raw.get("family") != fam:
        errs.append(f"family must be '{fam}' for this file (format {entry.format}, pdf_kind {entry.pdf_kind})")
    try:
        content = FAMILY_MODELS[fam].model_validate(raw)
    except ValidationError as e:
        for er in e.errors()[:15]:
            errs.append(f"schema: {'.'.join(map(str, er['loc']))}: {er['msg']}")
        return _reject(file_id, errs)
    if errs:
        return _reject(file_id, errs)
    werr: list[str] = []
    w = load_world(werr)
    errs += content_checks(entry, fam, raw, w)
    planted = {x["entry"]["id"]: x for x in Mf.load_planted()}
    if file_id in planted:
        errs += check_facts(entry, fam, raw, planted[file_id].get("facts", []), w)
    if errs:
        return _reject(file_id, errs)
    rerrs: list[str] = []
    try:
        path = render_entry(entry, content, w, rerrs)
    except Exception as e:
        rerrs.append(f"render failed: {type(e).__name__}: {e}")
        path = None
    if rerrs or path is None:
        return _reject(file_id, rerrs or ["render failed"])
    problem = reopen(path, entry.format, entry.pdf_kind)
    if problem:
        return _reject(file_id, [problem])
    CONTENT.mkdir(exist_ok=True)
    dst = CONTENT / f"{file_id}.json"
    if Path(content_path).resolve() != dst.resolve():
        shutil.copy(content_path, dst)
    state.mark(file_id, "accepted", summary=content.summary)
    # render any script exports whose source is this file
    extra = []
    for e in es.values():
        if e.pdf_kind == "export" and any(r.id == file_id and r.rel == "export_of" for r in e.related):
            from .render import render_export
            xe: list[str] = []
            p2 = render_export(e, w, xe)
            if p2 and not xe:
                state.mark(e.id, "accepted", summary=f"PDF export of {file_id}")
                extra.append(f"also rendered export {e.id} -> {p2}")
            else:
                extra.append(f"export {e.id} failed: {'; '.join(xe)}")
    rel = path.relative_to(path.parents[len(entry.path.split('/')) + 1]) if False else path
    return True, f"ACCEPTED {file_id} -> {rel}" + "".join("\n" + x for x in extra)


def _reject(file_id, errs):
    state.mark(file_id, "rejected", errors=errs)
    return False, f"REJECTED {file_id} ({len(errs)} reason(s)); fix all and resubmit:\n" + "\n".join(f"{i}. {e}" for i, e in enumerate(errs, 1))
