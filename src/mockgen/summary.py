"""Checkpoint reports (markdown)."""
from __future__ import annotations

from collections import Counter, defaultdict

import yaml

from . import manifest as Mf
from .paths import NAMES, ROOT
from .world import load_world


def world_summary() -> str:
    w = load_world([])
    g = w.group
    L = []
    A = L.append
    A(f"# World summary\n")
    A(f"**{g.name}** ({g.legal_name}), head office {g.head_office.city}, {g.head_office.country}. Platform formed {g.formed}; "
      f"group brand and template from {g.template.from_}. Integration programme \"{g.integration.name}\" since {g.integration.started}, "
      f"led by {w.people[g.integration.lead].canonical_name}.\n")
    A("| Firm | Legacy name | Focus | Location | Founded | Joined group | Files from | Dates |")
    A("|---|---|---|---|---|---|---|---|")
    for f in sorted(w.firms.values(), key=lambda f: f.joined_group):
        A(f"| {f.letter} | {f.legacy_name} | {f.service_focus} | {f.location.city}, {f.location.country} | {f.founded} | "
          f"{f.joined_group}{' (founder)' if f.role == 'founder' else ' (held back)' if f.role == 'held_back' else ''} | {f.file_era_start} | {f.date_convention} |")
    A("")
    A("**Key clients**\n")
    A("| Id | Client | Role | Names used (firm, from-to) |")
    A("|---|---|---|---|")
    for c in w.clients.values():
        if c.role == "background":
            continue
        vs = "; ".join(f"{v.name} ({v.firm}, {v.from_.year}-{v.to.year if v.to else 'now'})" for v in c.variants)
        A(f"| {c.id} | {c.canonical_name} | {c.role} | {vs} |")
    A(f"\nPlus {sum(1 for c in w.clients.values() if c.role == 'background')} background clients.\n")
    A("**Key staff**\n")
    A("| Id | Name | Variants | Role hint | Unit | Employed |")
    A("|---|---|---|---|---|---|")
    for p in w.people.values():
        if p.key:
            A(f"| {p.id} | {p.canonical_name} | {', '.join(p.variants)} | {p.role_hint} | {p.home_firm} | {p.joined}..{p.left or 'now'} |")
    st = Counter(p.status for p in w.projects.values())
    A(f"\nStaff directory: {len(w.people)} people ({sum(1 for p in w.people.values() if p.left)} leavers). "
      f"Projects: {len(w.projects)} ({', '.join(f'{k} {v}' for k, v in st.most_common())}). Compound series: {len(w.series)} "
      f"({sum(1 for s in w.series.values() if s.is_kinase)} kinase).\n")
    A("**Planted projects**\n")
    A("| Tag | Project | Firm | Client name used | Dates | Lead | Assays | Cpds | Turnaround | Price |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for p in sorted(w.projects.values(), key=lambda p: p.planted[0] if p.planted else "z"):
        if not p.planted:
            continue
        A(f"| {', '.join(p.planted)} | {p.id} {p.firm_project_id} | {p.firm} | {p.client_variant} | {p.dates.start or p.dates.quote}..{p.dates.completion or ''} | "
          f"{w.people[p.lead].canonical_name}{' (left ' + str(w.people[p.lead].left) + ')' if w.people[p.lead].left else ''} | {', '.join(p.assays)} | {p.n_compounds} | "
          f"{p.turnaround_days or '-'} d | {p.price.currency} {p.price.amount:,.0f} |")
    return "\n".join(L)


def planted_table() -> str:
    es = {e.id: e for e in Mf.load_entries([])}
    L = ["| Id | Role | Unit | Path | Format |", "|---|---|---|---|---|"]
    for item in Mf.load_planted():
        e = es.get(item["entry"]["id"])
        path = f"{'heldback_firm_G' if e and e.root == 'heldback' else 'archive'}/{Mf.full_path(e)}" if e else "(missing)"
        L.append(f"| {item['entry']['id']} | {item['label']} | {item['entry']['unit']} | `{path}` | {item['entry']['format']}{('/' + item['entry']['pdf_kind']) if item['entry'].get('pdf_kind') else ''} |")
    return "\n".join(L)


def counts_table() -> str:
    es = Mf.load_entries([])
    fmts = ["pptx", "ppt", "xlsx", "xls", "docx", "doc", "pdf", "csv"]
    L = ["| Unit | " + " | ".join(fmts) + " | of which scans | exports | junk | total |", "|---" * (len(fmts) + 5) + "|"]
    tot = Counter()
    for u in Mf.UNITS:
        c = Counter(e.format for e in es if e.unit == u)
        sc = sum(1 for e in es if e.unit == u and e.pdf_kind == "scan")
        ex = sum(1 for e in es if e.unit == u and e.pdf_kind == "export")
        jk = sum(1 for e in es if e.unit == u and e.doc_type == "junk")
        n = sum(c.values())
        tot.update(c); tot["scan"] += sc; tot["export"] += ex; tot["junk"] += jk; tot["total"] += n
        L.append(f"| {u} | " + " | ".join(str(c[f]) for f in fmts) + f" | {sc} | {ex} | {jk} | {n} |")
    L.append("| **all** | " + " | ".join(str(tot[f]) for f in fmts) + f" | {tot['scan']} | {tot['export']} | {tot['junk']} | **{tot['total']}** |")
    return "\n".join(L)


def screening_table() -> str:
    s = yaml.safe_load((NAMES / "screening.yaml").read_text())
    L = ["| Name | Kind | Depth | Checks run | Verdict | Notes |", "|---|---|---|---|---|---|"]
    for x in s:
        if x["kind"] == "client_background" and x["verdict"] != "rejected":
            continue
        srcs = sorted({c["source"] for c in x.get("checks", [])})
        L.append(f"| {x['name']} | {x['kind']} | {x['depth']} | {len(x.get('checks', []))}: {', '.join(srcs)} | {x['verdict']} | {(x.get('notes') or '')[:120]} |")
    bg = [x for x in s if x["kind"] == "client_background"]
    L.append(f"\nBackground clients: {sum(1 for x in bg if x['verdict'] != 'rejected')} kept after exact-name search, {sum(1 for x in bg if x['verdict'] == 'rejected')} rejected.")
    return "\n".join(L)
