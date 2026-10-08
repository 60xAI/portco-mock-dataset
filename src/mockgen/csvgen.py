"""Script-generated CSVs: staff directory, LIMS export, CRM client list."""
from __future__ import annotations

import csv
import io
import random
import zlib
from pathlib import Path

from .paths import SEED, TODAY
from .render import out_path, set_mtime


def _fmt(d, conv="UK"):
    if d is None:
        return ""
    return d.strftime("%d/%m/%Y") if conv == "UK" else d.strftime("%m/%d/%Y")


def staff_directory(w) -> tuple[list[str], list[list]]:
    cols = ["Employee ID", "Full name", "Display name", "Username", "Email", "Job title", "Legacy company", "Business unit",
            "Service line", "Office", "Start date", "Leave date", "Status", "Line manager"]
    rows = []
    units = {L: f for L, f in w.firms.items() if L != "G"}
    sl_names = {k: v["name"] for k, v in w.service_lines.items()}
    sl_names["admin"] = "Support functions"
    rnd = random.Random(SEED)
    for i, p in enumerate(sorted(w.people.values(), key=lambda x: (x.joined, x.id)), 1):
        if p.home_firm == "G":
            continue
        last = p.roles[-1]
        unit = last.unit
        legacy = w.group.name if p.home_firm == "HO" else units[p.home_firm].legacy_name
        bu = w.group.name if unit == "HO" else units[unit].short_name
        office = w.group.head_office.city if unit == "HO" else units[unit].location.city
        dom = w.group.email_domain if (p.left is None or p.left.year >= 2020) else (units[p.home_firm].email_domain if p.home_firm in units else w.group.email_domain)
        email = f"{p.username}@{dom}"
        disp = p.variants[0] if p.variants else p.canonical_name
        rows.append([f"E{1000 + i:05d}", p.canonical_name, disp, p.username, email, last.title, legacy, bu,
                     sl_names.get(p.service_line, p.service_line), office, _fmt(p.joined), _fmt(p.left),
                     "Left" if p.left else "Active", ""])
    # line managers: a deterministic senior person in same unit
    by_unit = {}
    for r in rows:
        by_unit.setdefault(r[7], []).append(r)
    for u, rs in by_unit.items():
        actives = [r for r in rs if r[12] == "Active"]
        for r in rs:
            if r[12] == "Left":
                continue
            if actives and rnd.random() < 0.85:
                m = rnd.choice(actives)
                if m is not r:
                    r[13] = m[1]
    return cols, rows


def lims_export(w) -> tuple[list[str], list[list]]:
    cols = ["LIMS_ID", "Legacy_Ref", "Site", "Client", "Service", "Assays", "Compounds", "Received", "Started", "Reported", "Status", "Study_Director", "Invoice_Value", "Currency"]
    rows = []
    stat = {"completed": "REPORTED", "in_progress": "IN PROGRESS", "lost": "QUOTE - NOT WON", "unanswered": "QUOTE - NO RESPONSE",
            "on_hold": "ON HOLD", "cancelled": "CANCELLED"}
    for p in sorted(w.projects.values(), key=lambda x: (x.dates.quote, x.id)):
        if p.firm == "G":
            continue
        f = w.firms[p.firm]
        conv = f.date_convention
        assays = []
        for a in p.assays:
            vs = (w.assays.get(a, {}).get("variants") or {}).get(p.firm) or []
            v = vs[0] if vs else w.assays.get(a, {}).get("name", a)
            assays.append(v if isinstance(v, str) else v.get("name"))
        lead = w.people[p.lead].username if p.lead in w.people else p.lead
        rows.append([p.lims_id, p.firm_project_id, f.short_name, p.client_variant.upper() if zlib.crc32(p.id.encode()) % 5 == 0 else p.client_variant,
                     w.service_lines.get(p.services[0], {}).get("name", p.services[0]) if p.services else "",
                     "; ".join(assays), p.n_compounds or "", _fmt(p.dates.quote, conv), _fmt(p.dates.start, conv), _fmt(p.dates.completion, conv),
                     stat[p.status], lead, f"{p.price.amount:.2f}" if p.status not in ("lost", "unanswered") else "", p.price.currency])
    return cols, rows


def client_list(w) -> tuple[list[str], list[list]]:
    cols = ["Account ID", "Account Name", "Source System", "Segment", "Country", "City", "First Activity", "Last Activity", "Owner", "Notes"]
    rows = []
    rnd = random.Random(SEED + 7)
    firstlast = {}
    for p in w.projects.values():
        k = (p.client_id, p.firm, p.client_variant)
        d = p.dates.quote
        a, b = firstlast.get(k, (d, d))
        firstlast[k] = (min(a, d), max(b, d))
    n = 0
    for c in sorted(w.clients.values(), key=lambda x: x.id):
        names = {}
        for v in c.variants:
            if v.firm == "G":
                continue
            names.setdefault((v.name, v.firm), v)
        if not names:
            names[(c.canonical_name, "HO")] = None
        for (name, firm), v in sorted(names.items()):
            n += 1
            fl = firstlast.get((c.id, firm, name))
            src = f"{w.firms[firm].short_name} CRM" if firm in w.firms else "Group CRM"
            note = ""
            if c.role == "q3_target" and rnd.random() < 0.5:
                note = "possible duplicate - check with finance"
            rows.append([f"ACC-{n:04d}", name, src, c.segment.replace("_", " "), c.location.country, c.location.city,
                         _fmt(fl[0]) if fl else "", _fmt(fl[1]) if fl else "", "", note])
    return cols, rows


GEN = {"staff_directory": staff_directory, "lims_export": lims_export, "client_list": client_list}


def render_csv(entry, w, errors) -> Path | None:
    gen = GEN.get(entry.doc_type)
    if not gen:
        errors.append(f"no CSV generator for doc_type {entry.doc_type}")
        return None
    cols, rows = gen(w)
    dst = out_path(entry)
    dst.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\r\n")
    wr.writerow(cols)
    wr.writerows(rows)
    dst.write_text(buf.getvalue(), encoding="utf-8-sig")
    set_mtime(dst, entry)
    return dst
