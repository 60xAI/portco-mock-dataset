"""Planted-answer file specs (manifest/planted.yaml), derived deterministically from the world.

Firm manifest agents copy each entry into their unit's manifest and fill in `path` and `filename`
(following `filename_hint`). Everything else stays as given. `facts` are checked by `mockgen submit`.
"""
from __future__ import annotations

import random
import zlib
from datetime import date, datetime, timedelta

import yaml

from .paths import MANIFEST, TODAY
from .world import load_world


def _dt(d: date, seed: str, hour_lo=8, hour_hi=18) -> datetime:
    r = random.Random(zlib.crc32(seed.encode()))
    while d.weekday() >= 5:
        d = d + timedelta(days=1)
    if d > TODAY:
        d = TODAY - timedelta(days=1)
    return datetime(d.year, d.month, d.day, r.randint(hour_lo, hour_hi - 1), r.randint(0, 59), r.randint(0, 59))


def template_for(w, unit: str, d: date) -> tuple[str, str]:
    if unit == "HO":
        return w.group.template.id, "group"
    for t in w.firms[unit].templates:
        if t.from_ <= d and (t.to is None or d <= t.to):
            return t.id, t.kind
    t = w.firms[unit].templates[-1]
    return t.id, t.kind


def employed_pick(w, unit, d, prefer=(), service=None):
    for pid in prefer:
        if pid in w.people and w.employed(pid, unit, d):
            return pid
    cands = sorted(p.id for p in w.people.values() if w.employed(p.id, unit, d) and (service is None or p.service_line == service))
    if not cands:
        cands = sorted(p.id for p in w.people.values() if w.employed(p.id, unit, d))
    if not cands:
        cands = sorted(p.id for p in w.people.values() if w.employed(p.id, None, d))
    return cands[zlib.crc32(f"{unit}{d}".encode()) % len(cands)]


def by_tag(w, tag):
    return next(p for p in w.projects.values() if tag in p.planted)


def build() -> str:
    errs: list[str] = []
    w = load_world(errs)
    if errs:
        return "world has errors; fix first"
    items = []
    n = 0

    def add(label, unit, fmt, doc_type, created: date, modified: date, author, saver, tags, *, pdf_kind=None, projects=(), client=None,
            variant=None, finish="final", mess=(), related=(), tier="orchestrator", length="", summary="", hint="", facts=(), golden=None):
        nonlocal n
        n += 1
        fid = f"P{n:02d}"
        tid, era = template_for(w, unit, created)
        c_dt = _dt(created, fid + "c")
        m_dt = max(c_dt + timedelta(minutes=37), _dt(modified, fid + "m"))
        e = {"id": fid, "unit": unit, "root": "heldback" if unit == "G" else "archive", "path": "<fill>", "filename": "<fill>",
             "format": fmt, "doc_type": doc_type, "pdf_kind": pdf_kind, "year": c_dt.year, "era": era, "template": tid,
             "created": c_dt.isoformat(), "modified": m_dt.isoformat(), "author": author, "last_saved_by": saver,
             "projects": list(projects), "client_id": client, "client_variant": variant, "finish": finish, "mess": list(mess),
             "planted": list(tags), "related": [{"id": i, "rel": r} for i, r in related], "tier": tier, "target_length": length,
             "summary": summary, "pilot": False}
        items.append({"label": label, "filename_hint": hint, "facts": list(facts), "golden": golden or {}, "entry": e})
        return fid

    D = w.firms["D"]
    bio = next(p.id for p in w.people.values() if p.role_hint == "bioinf_lead_D")
    integ = next(p.id for p in w.people.values() if p.role_hint == "integration_director")
    ceo = next(p.id for p in w.people.values() if p.role_hint == "group_ceo")
    q3 = next(c for c in w.clients.values() if c.role == "q3_target")
    look = next(c for c in w.clients.values() if c.role == "q3_lookalike")
    SLIDE = "Bioinformatics for drug discovery"

    # ---------------- Query 1: bioinformatics slide
    d_best = date(2025, 3, 11)
    p01 = add("q1 best: D capability deck, group template", "D", "pptx", "deck_capability", d_best, date(2025, 3, 27), bio,
              employed_pick(w, "D", date(2025, 3, 27), prefer=(bio,)), ["q1_correct_best"], length="14 slides",
              summary=f"{D.short_name} capability deck (2025, group template). Slide 3 '{SLIDE}' is the canonical one-slide explanation used in pitches.",
              hint="final client-facing capability deck, e.g. '<ShortName>_Capabilities_Bioinformatics_2025.pptx'",
              facts=[{"where": {"slide": 3}, "text": SLIDE}],
              golden={"query": 1, "role": "correct", "rank_hint": 1, "slide": 3})
    add("q1 best: PDF export of the best deck", "D", "pdf", "deck_capability", date(2025, 3, 27), date(2025, 3, 27), bio, bio,
        ["q1_correct_best_pdf"], pdf_kind="export", related=[(p01, "export_of")], tier="script", length="14 pages",
        summary="PDF export of the 2025 capability deck, sent to clients.", hint="same stem as the deck, .pdf",
        golden={"query": 1, "role": "correct", "rank_hint": 1, "page": 3})
    add("q1 alternative: older D capability deck (legacy template)", "D", "pptx", "deck_capability", date(2018, 5, 14), date(2018, 6, 4), bio, bio,
        ["q1_correct_alt_older"], length="18 slides", summary=f"{D.short_name} capability deck from 2018 in the legacy template, with a 'Bioinformatics in drug discovery' slide.",
        hint="older capability deck name in D's legacy style", facts=[{"where": {"slide": "any"}, "text": "Bioinformatics in drug discovery"}],
        golden={"query": 1, "role": "correct", "rank_hint": 2})
    add("q1 alternative + q3 bridge: head-office cross-sell deck reusing the slide", "HO", "pptx", "deck_pitch", date(2026, 5, 12), date(2026, 6, 2), integ,
        integ, ["q1_correct_alt_ho", "q3_bridge_deck"], client=q3.id, related=[(p01, "related")], length="12 slides",
        summary=f"Group cross-sell deck: reuses the D bioinformatics slide and uses {q3.canonical_name} (A/C/E history under three names; never bought D or F) as the worked example.",
        hint="group cross-sell / 'one Tarnovell' services deck",
        facts=[{"where": {"slide": "any"}, "text": SLIDE}] + [{"where": {"slide": "any"}, "text": v.name} for v in q3.variants if v.firm in "ACE"],
        golden={"query": 1, "role": "correct", "rank_hint": 3})
    add("q1 distractor: outdated D deck (.ppt)", "D", "ppt", "deck_capability", date(2012, 9, 18), date(2012, 10, 2), bio, bio,
        ["q1_distractor_outdated"], finish="superseded", length="16 slides",
        summary="2012 capability deck in the original legacy template; its bioinformatics slide predates current methods (microarrays, homology models).",
        hint="old .ppt in D's earliest naming style", facts=[{"where": {"slide": "any"}, "text": "Bioinformatics"}],
        golden={"query": 1, "role": "distractor", "why": "outdated version"})
    other_d = employed_pick(w, "D", date(2025, 4, 22), prefer=())
    add("q1 distractor: 'Copy of' near-duplicate of the best deck with a typo", "D", "pptx", "deck_capability", date(2025, 4, 22), date(2025, 4, 23),
        other_d, other_d, ["q1_distractor_typo_copy"], finish="superseded", mess=["copy_of", "typo"], related=[(p01, "copy_of")], tier="orchestrator",
        length="14 slides", summary="Copy of the 2025 capability deck saved by a colleague; slide 3 title has a typo ('Bioinfromatics') and an edited bullet.",
        hint="'Copy of <best deck filename>'", facts=[{"where": {"slide": 3}, "text": "Bioinfromatics for drug discovery"}],
        golden={"query": 1, "role": "distractor", "why": "near-duplicate with typo"})
    a_bd = employed_pick(w, "A", date(2023, 10, 3), prefer=("NS01",))
    add("q1 distractor: generic slide in an unrelated firm A deck", "A", "pptx", "deck_pitch", date(2023, 10, 3), date(2023, 10, 9), a_bd, a_bd,
        ["q1_distractor_generic_A"], length="10 slides",
        summary="Medicinal chemistry pitch with one generic 'integrated discovery' slide that mentions bioinformatics in passing.",
        hint="pitch deck in A's style", facts=[{"where": {"slide": "any"}, "text": "bioinformatics"}],
        golden={"query": 1, "role": "distractor", "why": "generic mention in unrelated deck"})
    add("q1 distractor: superseded v2 draft of the best deck", "D", "pptx", "deck_capability", date(2025, 2, 17), date(2025, 2, 28), bio, bio,
        ["q1_distractor_v2_draft"], finish="superseded", mess=["version_suffix", "draft_mark", "comments"], related=[(p01, "version_of")],
        length="15 slides", summary="Earlier v2 draft of the 2025 capability deck with reviewer notes and an unfinished bioinformatics slide.",
        hint="same stem as the best deck with _v2 / DRAFT", facts=[{"where": {"slide": "any"}, "text": "Bioinformatics"}],
        golden={"query": 1, "role": "distractor", "why": "older draft version"})
    add("q1 distractor: D training deck", "D", "pptx", "deck_training", date(2021, 6, 8), date(2021, 6, 15), bio, bio,
        ["q1_distractor_training"], length="20 slides", summary="Internal training deck introducing bioinformatics tools to chemists; not a client-facing slide.",
        hint="training deck name", facts=[{"where": {"slide": "any"}, "text": "bioinformatics"}],
        golden={"query": 1, "role": "distractor", "why": "internal training material"})

    # ---------------- Query 2: hERG + CYP on a kinase series
    for tag in ["q2_correct_B1", "q2_correct_B2", "q2_correct_C1", "q2_correct_C2"]:
        p = by_tag(w, tag)
        f = w.firms[p.firm]
        lead = p.lead
        bd = employed_pick(w, p.firm, p.dates.quote, prefer=(lead,))
        prop_fmt = "doc" if p.dates.quote.year < 2012 and p.firm == "B" else "docx"
        price_fact = {"kind": "price", "project": p.id}
        prop = add(f"{tag}: proposal with price and turnaround", p.firm, prop_fmt, "word_proposal", p.dates.quote, p.dates.quote + timedelta(days=1),
                   bd, bd, [tag + "_proposal"], projects=[p.id], client=p.client_id, variant=p.client_variant, length="5-7 pages",
                   summary=f"Proposal {p.firm_project_id} to {p.client_variant}: hERG + CYP panel on {p.n_compounds} kinase-series compounds; price and turnaround stated.",
                   hint="proposal/quote in the firm's naming style, includes the project id",
                   facts=[price_fact, {"text": str(p.n_compounds)}, {"text": p.client_variant}, {"any_of": ["3 weeks", "three weeks", "15 working days", "21 days", "3-week", "three-week", "15 business days"]}],
                   golden={"query": 2, "role": "correct", "project": p.id, "carries": "price, turnaround, scope"})
        wb = add(f"{tag}: results workbook with benchmark table", p.firm, "xlsx", "wb_results", p.dates.start, p.dates.completion, lead, lead,
                 [tag + "_results"], projects=[p.id], client=p.client_id, variant=p.client_variant, related=[(prop, "results_for")], length="4-5 sheets",
                 summary=f"Results workbook for {p.firm_project_id}: hERG IC50 and 5-isoform CYP inhibition for {p.n_compounds} compounds, with a benchmark summary sheet.",
                 hint="results workbook name with project id",
                 facts=[{"where": {"sheet": "any"}, "text": "{{%s:herg.median_ic50_uM}}" % p.id}, {"where": {"sheet": "any"}, "table_ref": f"{p.id}:benchmark"}],
                 golden={"query": 2, "role": "correct", "project": p.id, "carries": "benchmark table (sheet)"})
        add(f"{tag}: study report PDF that summarises the benchmark table", p.firm, "pdf", "report_study", p.dates.completion - timedelta(days=2), p.dates.completion,
            lead, lead, [tag + "_report"], pdf_kind="native", projects=[p.id], client=p.client_id, variant=p.client_variant,
            related=[(prop, "report_for"), (wb, "related")], length="10-16 pages",
            summary=f"Final report {p.firm_project_id}: hERG and CYP results for {p.n_compounds} kinase-series compounds, with the benchmark summary table on an early page.",
            hint="final report PDF name",
            facts=[{"table_ref": f"{p.id}:benchmark"}, {"text": p.client_variant}, {"text": str(p.n_compounds)}],
            golden={"query": 2, "role": "correct", "project": p.id, "carries": "benchmark summary table (page)"})
    for tag, kinds in [("q2_distractor_herg_only", ["wb_results", "report_study"]), ("q2_distractor_cyp_other_chemotype", ["wb_results", "report_study"]),
                       ("q2_distractor_right_client_wrong_assay", ["word_proposal", "report_study"])]:
        p = by_tag(w, tag)
        for k in kinds:
            if k == "word_proposal":
                bd = employed_pick(w, p.firm, p.dates.quote, prefer=(p.lead,))
                add(f"{tag}: proposal", p.firm, "docx", k, p.dates.quote, p.dates.quote + timedelta(days=2), bd, bd, [tag], projects=[p.id],
                    client=p.client_id, variant=p.client_variant, length="4-6 pages", summary=f"Proposal {p.firm_project_id}: {p.title}.",
                    hint="proposal name", facts=[{"kind": "price", "project": p.id}], golden={"query": 2, "role": "distractor", "why": tag})
            elif k == "wb_results":
                add(f"{tag}: results workbook", p.firm, "xlsx", k, p.dates.start, p.dates.completion, p.lead, p.lead, [tag], projects=[p.id],
                    client=p.client_id, variant=p.client_variant, length="3 sheets", summary=f"Results workbook {p.firm_project_id}: {p.title}.",
                    hint="results workbook name", facts=[], golden={"query": 2, "role": "distractor", "why": tag})
            else:
                add(f"{tag}: report", p.firm, "pdf", k, p.dates.completion - timedelta(days=2), p.dates.completion, p.lead, p.lead, [tag],
                    pdf_kind="native", projects=[p.id], client=p.client_id, variant=p.client_variant, length="8-12 pages",
                    summary=f"Report {p.firm_project_id}: {p.title}.", hint="report PDF name", facts=[{"text": p.client_variant}],
                    golden={"query": 2, "role": "distractor", "why": tag})
    hr = employed_pick(w, "HO", date(2026, 9, 1), prefer=())
    add("q2 who-to-ask: group staff directory (CSV)", "HO", "csv", "staff_directory", date(2026, 9, 1), date(2026, 9, 14), hr, hr, ["q2_staff_directory"],
        tier="script", length="~170 rows", summary="Group staff directory export (A-F + head office) with start and leave dates.",
        hint="HR export e.g. 'Staff_Directory_Export_2026-09.csv'", golden={"query": 2, "role": "supporting", "carries": "who ran each project, leave dates"})
    add("q2/q3: group LIMS export (CSV)", "HO", "csv", "lims_export", date(2026, 8, 20), date(2026, 8, 20), integ, integ, ["q2_lims_export"],
        tier="script", length="~115 rows", summary="Consolidated LIMS export (A-F) with LIMS IDs, legacy refs, clients as recorded, assays, dates and status.",
        hint="LIMS export name", golden={"query": 2, "role": "supporting", "carries": "project ids in LIMS format"})
    add("q3: CRM client list export (CSV, unmerged variants)", "HO", "csv", "client_list", date(2026, 7, 7), date(2026, 7, 7), integ, integ,
        ["q3_crm_export"], tier="script", length="~110 rows", summary="CRM account export from all legacy systems; variant names appear as separate accounts.",
        hint="CRM export name", golden={"query": 3, "role": "supporting", "carries": "variants as separate accounts"})

    # ---------------- Query 3: cross-sell
    for tag, fmt, k, why in [("q3_target_A", "doc", "report_client", "A history"), ("q3_target_C", "pdf", "report_study", "C history"),
                             ("q3_target_E", "docx", "word_proposal", "E history (names former variant)")]:
        p = by_tag(w, tag)
        prior = [v.name for v in q3.variants if v.firm != "G" and v.name != p.client_variant and v.from_ < p.dates.quote]
        facts = [{"text": p.client_variant}]
        if tag == "q3_target_E" and prior:
            facts.append({"text": prior[-1]})
        d0 = p.dates.quote if k == "word_proposal" else (p.dates.completion or p.dates.quote)
        add(f"{tag}: {k}", p.firm, fmt, k, d0 - timedelta(days=1 if k != "word_proposal" else 0), d0 + timedelta(days=1), p.lead, p.lead, [tag],
            pdf_kind="native" if fmt == "pdf" else None, projects=[p.id], client=q3.id, variant=p.client_variant, length="6-12 pages",
            summary=f"{k.replace('_', ' ')} for {p.client_variant} ({p.firm_project_id}): {p.title}." + (f" Names the client as '{p.client_variant} (formerly {prior[-1]})'." if tag == "q3_target_E" and prior else ""),
            hint="name in the firm's style", facts=facts, golden={"query": 3, "role": "correct", "project": p.id, "variant": p.client_variant})
    add("q3 bridge: group client identity bridge workbook", "HO", "xlsx", "wb_other", date(2026, 3, 9), date(2026, 8, 25), integ, integ,
        ["q3_bridge_alias_workbook"], client=q3.id, length="3 sheets",
        summary=f"Integration workbook mapping legacy client names to group accounts; links {q3.canonical_name}'s A/C/E names, flags {look.canonical_name} as a different company.",
        hint="client mapping / identity bridge workbook",
        facts=[{"text": v.name} for v in q3.variants if v.firm in "ACE"] + [{"text": look.canonical_name}],
        golden={"query": 3, "role": "correct", "carries": "variant bridge"})
    add("q3 bridge: cross-sell white-space matrix", "HO", "xlsx", "wb_other", date(2026, 6, 15), date(2026, 9, 2), integ,
        employed_pick(w, "HO", date(2026, 9, 2), prefer=(integ,)), ["q3_whitespace_matrix"], client=q3.id, finish="draft", mess=["half_filled"],
        length="2 sheets", summary="Client x service-line matrix for top accounts showing which legacy firms each client has bought from; half-finished.",
        hint="cross-sell matrix workbook", facts=[{"text": q3.canonical_name}], golden={"query": 3, "role": "correct", "carries": "white space"})
    p = by_tag(w, "q3_lookalike")
    add("q3 distractor: lookalike client proposal", p.firm, "docx", "word_proposal", p.dates.quote, p.dates.quote + timedelta(days=1), p.lead, p.lead,
        ["q3_lookalike"], projects=[p.id], client=look.id, variant=p.client_variant, length="5 pages",
        summary=f"Proposal to {p.client_variant} ({p.firm_project_id}), a different company from {q3.canonical_name}.",
        hint="proposal name", facts=[{"text": p.client_variant}], golden={"query": 3, "role": "distractor", "why": "similar client name"})

    # ---------------- Query 4: firm G (held back)
    for tag in ["q4_G1", "q4_G2"]:
        p = by_tag(w, tag)
        prop = None
        if tag == "q4_G1":
            prop = add(f"{tag}: proposal", "G", "docx", "word_proposal", p.dates.quote, p.dates.quote + timedelta(days=1), p.lead, p.lead, [tag + "_proposal"],
                       projects=[p.id], client=p.client_id, variant=p.client_variant, length="6 pages",
                       summary=f"Proposal {p.firm_project_id} to {p.client_variant}: in vitro safety pharmacology (hERG + CYP) on {p.n_compounds} kinase compounds.",
                       hint="proposal name", facts=[{"kind": "price", "project": p.id}, {"text": p.client_variant}, {"text": str(p.n_compounds)}],
                       golden={"query": 4, "role": "correct", "project": p.id, "depends_on_G": True})
        wb = add(f"{tag}: results workbook", "G", "xlsx", "wb_results", p.dates.start, p.dates.completion, p.lead, p.lead, [tag + "_results"],
                 projects=[p.id], client=p.client_id, variant=p.client_variant, related=[(prop, "results_for")] if prop else [], length="4 sheets",
                 summary=f"Results workbook {p.firm_project_id}: hERG and CYP data for {p.n_compounds} compounds with benchmark sheet.",
                 hint="results workbook name", facts=[{"where": {"sheet": "any"}, "table_ref": f"{p.id}:benchmark"}],
                 golden={"query": 4, "role": "correct", "project": p.id, "depends_on_G": True})
        add(f"{tag}: report", "G", "pdf", "report_study", p.dates.completion - timedelta(days=2), p.dates.completion, p.lead, p.lead, [tag + "_report"],
            pdf_kind="native", projects=[p.id], client=p.client_id, variant=p.client_variant, related=[(wb, "related")], length="12-18 pages",
            summary=f"Final report {p.firm_project_id} for {p.client_variant}, summarising the benchmark table.",
            hint="report PDF name", facts=[{"table_ref": f"{p.id}:benchmark"}, {"text": p.client_variant}],
            golden={"query": 4, "role": "correct", "project": p.id, "depends_on_G": True})

    # ---------------- Query 5: structural biology (no cryo-EM)
    p = by_tag(w, "q5_structbio_D")
    add("q5 closest work: D crystallography-based docking report", "D", "pdf", "report_client", p.dates.completion - timedelta(days=3), p.dates.completion,
        p.lead, p.lead, ["q5_structbio_D"], pdf_kind="native", projects=[p.id], client=p.client_id, variant=p.client_variant, length="10-14 pages",
        summary=f"Structure-based design report {p.firm_project_id}: docking into published-style X-ray structures. ",
        hint="report PDF name", facts=[{"any_of": ["crystal structure", "crystallograph", "X-ray"]}],
        golden={"query": 5, "role": "closest_related"})
    p = by_tag(w, "q5_structbio_A")
    add("q5 closest work: A structural biology collaboration readout", "A", "pptx", "deck_readout", (p.dates.completion or p.dates.start) - timedelta(days=4),
        p.dates.completion or p.dates.start, p.lead, p.lead, ["q5_structbio_A"], projects=[p.id], client=p.client_id, variant=p.client_variant, length="12 slides",
        summary=f"Readout {p.firm_project_id}: chemistry guided by X-ray co-crystal structures from a collaborator. ",
        hint="readout deck name", facts=[{"any_of": ["co-crystal", "X-ray", "crystal structure"]}],
        golden={"query": 5, "role": "closest_related"})

    MANIFEST.mkdir(exist_ok=True)
    (MANIFEST / "planted.yaml").write_text(yaml.safe_dump({"planted": items}, sort_keys=False, allow_unicode=True, width=140))
    return f"wrote {len(items)} planted entries -> manifest/planted.yaml"
