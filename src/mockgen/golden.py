"""golden_set.json: planted answers and distractors located by partitioning rendered files with `unstructured`
(slide number -> page_number for pptx; sheet index -> page_number for xlsx), as AI Brain's parser does."""
from __future__ import annotations

import json
import re
from collections import defaultdict

from . import manifest as Mf
from .paths import OUTPUT, ROOT
from .render import out_path, resolve_text, get_table
from .textscan import norm
from .world import load_world

QUERIES = {
    1: "I need a slide explaining bioinformatics for drug discovery for a pitch tomorrow.",
    2: "hERG and CYP inhibition screening on ~40 compounds from a kinase series, turnaround under 3 weeks.",
    3: "Show {client}'s full history across all the legacy companies and the service lines it has never bought.",
    4: "(after ingesting the held-back firm G archive) Re-run query 2: hERG and CYP inhibition screening on ~40 compounds from a kinase series, turnaround under 3 weeks.",
    5: "Have we done any cryo-EM work?",
}


def partition(path):
    from unstructured.partition.auto import partition
    kw = {}
    if path.suffix.lower() == ".pdf":
        kw["strategy"] = "fast"
    return partition(filename=str(path), **kw)


def locate(elements, needles: list[str]):
    """Return sorted page numbers (and sheet names) whose text contains any needle."""
    pages, names = set(), set()
    ns = [norm(n) for n in needles if n]
    for el in elements:
        t = norm(str(el))
        if any(n and n in t for n in ns):
            pn = getattr(el.metadata, "page_number", None)
            if pn:
                pages.add(pn)
            nm = getattr(el.metadata, "page_name", None)
            if nm:
                names.add(nm)
    return sorted(pages), sorted(names)


def mentioned_any(hits) -> bool:
    return any(pg for _, pg, _ in hits)


def locate_facts(elements, fact_needles: list[list[str]]):
    """Tighter locator: score pages by how many distinct facts they carry, ignoring facts that appear on most
    pages (headers, footers). Returns (answer pages, answer sections, all pages mentioned)."""
    all_pages = {getattr(el.metadata, "page_number", None) for el in elements} - {None}
    heading, hits = None, []
    for el in elements:
        if type(el).__name__ == "Title":
            heading = str(el).strip()[:120]
        t = norm(str(el))
        for i, ns in enumerate(fact_needles):
            if any(n and norm(n) in t for n in ns):
                hits.append((i, getattr(el.metadata, "page_number", None), heading))
    per_fact = defaultdict(set)
    for i, pg, _ in hits:
        if pg:
            per_fact[i].add(pg)
    broad = {i for i, pgs in per_fact.items() if len(all_pages) >= 4 and len(pgs) > len(all_pages) / 2}
    score = defaultdict(set)
    sec_score = defaultdict(set)
    for i, pg, h in hits:
        if i in broad:
            continue
        if pg:
            score[pg].add(i)
        if h:
            sec_score[h].add(i)
    if not score and mentioned_any(hits):
        # every fact sits in headers/footers: the cover page is the answer
        first = min(pg for _, pg, _ in hits if pg)
        score[first] = {-1}
    best = max((len(v) for v in score.values()), default=0)
    answer = sorted(pg for pg, v in score.items() if len(v) == best) if best else []
    sbest = max((len(v) for v in sec_score.values()), default=0)
    sections = [h for h, v in sec_score.items() if len(v) == sbest][:3] if sbest else []
    mentioned = sorted({pg for _, pg, _ in hits if pg})
    return answer, sections, mentioned


def needles_for(item, w):
    return [n for g in fact_groups(item, w) for n in g]


def fact_groups(item, w):
    groups = []
    for f in item.get("facts", []):
        out = []
        if "text" in f:
            out.append(resolve_text(f["text"]))
        if "any_of" in f:
            out += f["any_of"]
        if "table_ref" in f:
            t = get_table(f["table_ref"])
            if t:
                out.append(t["columns"][0])
                out += [str(r[1]) for r in t["rows"][:1]]
        if f.get("kind") == "price":
            p = w.projects[f["project"]]
            out.append(f"{p.price.amount:,.0f}")
        if out:
            groups.append(out)
    return groups


def build_golden() -> str:
    w = load_world([])
    es = {e.id: e for e in Mf.load_entries([])}
    q3 = next(c for c in w.clients.values() if c.role == "q3_target")
    queries = defaultdict(lambda: {"expected": [], "distractors": [], "supporting": [], "closest_related": []})
    missing = []
    for item in Mf.load_planted():
        gid = item["entry"]["id"]
        g = item.get("golden") or {}
        if not g or gid not in es:
            continue
        e = es[gid]
        p = out_path(e)
        if not p.exists():
            missing.append(gid)
            continue
        rec = {"file_id": gid, "path": f"{'heldback_firm_G' if e.root == 'heldback' else 'archive'}/{Mf.full_path(e)}",
               "format": e.format, "fact": e.summary, "depends_on_firm_G": e.unit == "G"}
        if e.format != "csv":
            try:
                els = partition(p)
                needles = needles_for(item, w)
                if e.pdf_kind == "export":
                    src = next((x for x in Mf.load_planted() if x["entry"]["id"] == e.related[0].id), None) if e.related else None
                    needles = needles_for(src, w) if src else needles
                pages, names = locate(els, needles)
                groups = fact_groups(src if e.pdf_kind == "export" and src else item, w) if e.pdf_kind == "export" else fact_groups(item, w)
                answer, sections, mentioned = locate_facts(els, groups)
                pids = [g["project"]] if g.get("project") else list(e.projects)
                if not answer and not sections and pids:
                    ids = [x for pid in pids for x in (w.projects[pid].firm_project_id, w.projects[pid].lims_id)]
                    answer, sections, mentioned = locate_facts(els, [ids])
                    if not pages:
                        pages, names = locate(els, ids)
                if answer:
                    rec["answer_page_number"] = answer
                if sections:
                    rec["answer_section"] = sections
                if "slide" in g and e.format in ("pptx", "ppt"):
                    rec["slide"] = g["slide"]
                    rec["unstructured_page_number"] = pages
                    if g["slide"] not in pages:
                        rec["warning"] = f"expected slide {g['slide']} not among unstructured pages {pages}"
                elif "page" in g:
                    rec["page"] = g["page"]
                    rec["unstructured_page_number"] = pages
                    if g["page"] not in pages:
                        rec["warning"] = f"expected page {g['page']} not among unstructured pages {pages}"
                else:
                    rec["unstructured_page_number"] = pages
                if names:
                    rec["sheet"] = names
            except Exception as ex:
                rec["warning"] = f"partition failed: {type(ex).__name__}: {ex}"
        bucket = {"correct": "expected", "distractor": "distractors", "supporting": "supporting", "closest_related": "closest_related"}[g.get("role", "supporting")]
        if g.get("why"):
            rec["why"] = g["why"]
        if g.get("rank_hint"):
            rec["rank_hint"] = g["rank_hint"]
        if g.get("project"):
            pr = w.projects[g["project"]]
            rec["project"] = {"id": pr.id, "firm_id": pr.firm_project_id, "lims_id": pr.lims_id, "client_name_used": pr.client_variant,
                              "lead": w.people[pr.lead].canonical_name, "lead_left": str(w.people[pr.lead].left or ""),
                              "n_compounds": pr.n_compounds, "turnaround_days": pr.turnaround_days, "price": f"{pr.price.currency} {pr.price.amount:,.0f}",
                              "year": (pr.dates.start or pr.dates.quote).year}
        queries[g["query"]][bucket].append(rec)
    out = {"dataset": "portco-mock-dataset", "generated_by": "mockgen golden", "page_numbering": "unstructured page_number (pptx: slide index; pdf: page; xlsx: sheet index; sheet name in `sheet`)",
           "queries": []}
    for q in sorted(QUERIES):
        d = queries[q]
        out["queries"].append({"id": q, "query": QUERIES[q].format(client=q3.canonical_name), "depends_on_firm_G": q == 4,
                               "expected": d["expected"], "distractors": d["distractors"], "supporting": d["supporting"],
                               "closest_related": d["closest_related"],
                               **({"expected_answer": "No evidence of cryo-EM work in the archive; closest related work is structural-biology-guided design."} if q == 5 else {}),
                               **({"bought_from": sorted({p.firm for p in w.projects.values() if p.client_id == q3.id and p.firm != "G"}),
                                   "white_space": [f"{f.letter} {f.legacy_name} ({f.service_focus})" for f in w.firms.values()
                                                   if f.letter != "G" and not any(p.client_id == q3.id and p.firm == f.letter for p in w.projects.values())],
                                   "client_names": sorted({v.name for v in q3.variants if v.firm != "G"})} if q == 3 else {})})
    (OUTPUT / "golden_set.json").parent.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "golden_set.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    warns = sum(1 for q in out["queries"] for k in ("expected", "distractors", "closest_related") for r in q[k] if "warning" in r)
    return f"golden set -> {OUTPUT / 'golden_set.json'}; {warns} warnings; not rendered yet: {missing}"
