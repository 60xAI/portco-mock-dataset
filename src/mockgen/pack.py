"""`mockgen pack <file-id>`: self-contained context pack for one file (~8k tokens max)."""
from __future__ import annotations

import json

import yaml

from . import manifest as Mf
from . import state
from .paths import CONTENT, EXEMPLARS, NUMBERS, ROOT, TODAY
from .schemas import schema_text
from .world import load_world

MESS_HELP = {
    "copy_of": "it is a 'Copy of' another file: mostly the same content, slightly edited",
    "version_suffix": "an intermediate version (v2/v3/FINAL_final): close to the final but with differences",
    "unhelpful_name": "the filename says nothing useful; the content is still real",
    "duplicate_across_firms": "a deck copied from another firm's share, lightly rebadged",
    "typo": "contains a few realistic typos",
    "tracked_changes": "add 1-3 tracked_changes (document) from a reviewer",
    "comments": "add 1-3 reviewer comments (document comments / workbook cell comments / slide notes)",
    "tbc_placeholders": "leave [TBC] / XX% placeholders where facts weren't known yet",
    "mixed_units": "mix units inconsistently in places (e.g. µM and nM, mg/mL and mg/ml)",
    "inconsistent_dates": "use two different date formats in the file",
    "leaver_folder": "found on a departed employee's old laptop: personal working copy, informal notes",
    "half_filled": "a tracker/matrix only partly filled in; blank rows and cells left",
    "stale_template": "uses an outdated template on purpose",
    "draft_mark": "mark DRAFT (watermark or title) and leave obvious gaps",
    "empty_sections": "leave some template sections empty",
    "near_empty": "nearly empty: a title and a line or two, nothing else",
}

FINISH_HELP = {
    "final": "complete and polished",
    "draft": "a draft: incomplete sections, DRAFT marks, open questions",
    "interim": "interim: partial results, clearly labelled interim, final conclusions pending",
    "superseded": "an older/superseded version of a later file",
    "abandoned": "work stopped part-way; ends abruptly or with open TODOs",
    "empty_template": "an empty or near-empty template with headings and placeholders only",
}

PROHIBITIONS = """- No real company, CRO, vendor, pharma, instrument-maker or person names. Use ONLY the organisations and people in this pack
  (or other people/clients listed in the world for this firm). Generic reagents/reference compounds are fine (E-4031, ketoconazole, verapamil).
- No new numbers for assay results, prices, compound counts or turnaround: take them from the numbers section via {{PRJnnnn:key}}
  placeholders or table_ref / data_refs. You may write qualitative statements and non-result numbers (concentrations tested, n, protocol settings).
- Don't contradict the world (dates, who worked where and when, client names in use at the time, assay house names).
- Nothing outside the file's era: no later client names, people who joined later, later technology or later group branding.
- Never mention cryo-EM. No structural biology unless the pack says so.
- Write in the firm's voice and terminology; use its date format and units.
- Output ONLY the JSON object (no markdown fences) to the content path given below."""


def _person_line(w, pid, on):
    p = w.people.get(pid)
    if not p:
        return f"{pid}: unknown"
    r = w.role_at(pid, on)
    return (f"{pid}: {p.canonical_name}{' (Dr)' if p.title == 'Dr' else ''} - {r.title + ' at ' + r.unit if r else 'not employed then'} on {on}; "
            f"name variants {p.variants}; employed {p.joined}..{p.left or 'now'}")


def _brand(w, e):
    if e.unit == "HO":
        return w.group.name, w.group.template
    f = w.firms[e.unit]
    t = next((t for t in f.templates if t.id == e.template), None) or w.group.template
    return f.legacy_name, t


def build_pack(file_id: str) -> str:
    es = {e.id: e for e in Mf.load_entries([])}
    if file_id not in es:
        return f"unknown file id {file_id}"
    e = es[file_id]
    w = load_world([])
    fam = Mf.family(e)
    out = []
    A = out.append
    A(f"# Context pack: {file_id}\n")
    A(f"Write the content JSON for ONE file. Family: **{fam}**. Save it to `{CONTENT}/{file_id}.json`, then run from `{ROOT}`:\n"
      f"`uv run mockgen submit {file_id} content/{file_id}.json`. On rejection, fix every numbered reason and resubmit (aim to pass in one retry).\n")
    A("## File entry\n```yaml\n" + yaml.safe_dump(e.model_dump(mode="json"), sort_keys=False, allow_unicode=True, width=120) + "```")
    A(f"Finish state: **{e.finish}**: {FINISH_HELP.get(e.finish, '')}.")
    if e.mess:
        A("Texture to apply: " + "; ".join(f"`{m}`: {MESS_HELP.get(m, m)}" for m in e.mess) + ".")
    A(f"Target length: {e.target_length}. The file is dated {e.created:%Y-%m-%d} (created) to {e.modified:%Y-%m-%d} (last saved). World today is {TODAY}.\n")

    # style
    legacy, t = _brand(w, e)
    A("## Firm style and era")
    if e.unit == "HO":
        g = w.group
        A(f"Unit: group head office of **{g.name}** ({g.head_office.city}). Brand line: '{t.brand_line}'. Footer: '{t.footer_text}'. "
          f"Integration programme: {g.integration.name} ({g.integration.status}). Workstreams: " +
          "; ".join(f"{x.name} [{x.status}] {x.notes}" for x in g.integration.workstreams))
        A("Group history: " + " ".join(g.history))
        A("Firms in the group: " + "; ".join(f"{f.letter} {f.legacy_name} ({f.short_name}, {f.service_focus}, {f.location.city} {f.location.country}, joined {f.joined_group})" for f in w.firms.values()))
    else:
        f = w.firms[e.unit]
        A(f"**{f.legacy_name}** (\"{f.short_name}\"), {f.service_focus}, {f.location.city}, {f.location.country}. Founded {f.founded}; "
          f"{'founding firm of the group' if f.role == 'founder' else ('acquired by ' + w.group.name + ' on ' + str(f.joined_group)) if f.role == 'acquired' else 'acquired ' + str(f.joined_group) + ' (archive not yet integrated)'}.")
        A(f"Template in force: `{t.id}` ({t.kind}): brand line '{t.brand_line}', footer '{t.footer_text}', fonts {t.font_heading}/{t.font_body}. "
          f"{'Legacy era: the group does not exist in this firm’s documents yet unless already acquired; use the legacy brand only.' if t.kind == 'legacy' else 'Post-acquisition: show the brand line with the group name.'}")
        if e.modified.date() < w.group.template.from_:
            A(f"Group naming: the '{w.group.short_name}' brand did not exist until {w.group.template.from_}. Before that, refer to the group (if at all) as 'the Vellacombe group'.")
        A(f"Voice: {f.voice}")
        A(f"Terminology (house term for generic term): {json.dumps(f.terminology, ensure_ascii=False)}")
        A(f"Dates: {f.date_convention} convention, formats {f.date_formats}. Units: {f.units_notes}")
        A(f"IDs: project {f.id_formats.project_id}; LIMS {f.id_formats.lims_id}; reports {f.id_formats.report_id}. Typical lengths: {f.typical_lengths}")
        A(f"Transition rules: {f.transition_rules}")
        A("History: " + " ".join(f.history))
        hv = {a: v.get(e.unit) for a, v in ((k, (x.get('variants') or {})) for k, x in w.assays.items()) if v.get(e.unit)}
        if hv:
            A("Assay house names at this firm: " + "; ".join(f"{a}: {', '.join(x if isinstance(x, str) else x.get('name') for x in v)}" for a, v in hv.items()))
    A("")

    # people
    A("## People")
    on_c, on_m = e.created.date(), e.modified.date()
    A("- author " + _person_line(w, e.author, on_c))
    A("- last saved by " + _person_line(w, e.last_saved_by, on_m))
    pids = set()
    for pj in e.projects:
        p = w.projects.get(pj)
        if p:
            pids |= {p.lead, *p.team}
    for pid in sorted(pids - {e.author, e.last_saved_by}):
        A("- project " + _person_line(w, pid, on_c))
    unit_people = [p for p in w.people.values() if (p.home_firm == e.unit or any(r.unit == e.unit for r in p.roles)) and w.employed(p.id, None, on_c)
                   and p.id not in pids | {e.author, e.last_saved_by}]
    if unit_people:
        A("- other colleagues you may name (employed then): " + "; ".join(f"{p.canonical_name} ({(w.role_at(p.id, on_c) or p.roles[-1]).title})" for p in unit_people[:12]))
    A("")

    # projects and numbers
    for pj in e.projects:
        p = w.projects.get(pj)
        if not p:
            continue
        A(f"## Project {pj}")
        d = p.model_dump(mode="json")
        d.pop("planted", None)
        A("```yaml\n" + yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=120) + "```")
        A("Assays: " + "; ".join(f"{a} = {w.assays[a]['name']} (house names: {(w.assays[a].get('variants') or {}).get(p.firm) or '-'})" for a in p.assays if a in w.assays))
        if p.series_id and p.series_id in w.series:
            s = w.series[p.series_id]
            A(f"Series {s.id}: {s.name}, {s.chemotype}, target {s.target}, compound prefix {s.compound_prefix}.")
        nf = NUMBERS / f"{pj}.json"
        if nf.exists():
            nd = json.loads(nf.read_text())
            vals = {k: v for k, v in nd["values"].items() if k.count(".") < 2}
            A(f"Numbers for {pj} (write `{{{{{pj}:key}}}}` in any text to insert a value):")
            A("```json\n" + json.dumps(vals, ensure_ascii=False) + "\n```")
            per = [k for k in nd["values"] if k.count(".") >= 2][:4]
            if per:
                A(f"Per-compound keys also exist, e.g. {per}.")
            if nd["tables"]:
                A(f"Tables (embed with `{{\"table_ref\": \"{pj}:<key>\"}}` in a slide/section, or `data_refs` in a sheet; they render the full data):")
                for k, t in nd["tables"].items():
                    A(f"- `{pj}:{k}`: {t['title']}; {len(t['rows'])} rows; columns {t['columns']}; first row {t['rows'][0] if t['rows'] else '-'}")
            else:
                A("No result tables (no lab results for this status).")
        A("")
    # client
    if e.client_id and e.client_id in w.clients:
        c = w.clients[e.client_id]
        A("## Client")
        A(f"Use the name **{e.client_variant or c.canonical_name}** for this file (that is what {e.unit} called them then). {c.segment}, {c.location.city}, {c.location.country}.")
        if e.unit == "HO" or any(t.startswith("q3") for t in e.planted):
            A(f"All names known for this client (bridging documents may list them): {[ (v.name, v.firm, str(v.from_), str(v.to)) for v in c.variants if v.firm != 'G']}. Notes: {c.notes}")
        A("")
    # related
    if e.related:
        A("## Related files")
        sums = state.summaries([r.id for r in e.related])
        for r in e.related:
            re_ = es.get(r.id)
            line = f"- {r.rel} {r.id}"
            if re_:
                line += f" ({Mf.full_path(re_)}, {re_.modified:%Y-%m-%d}): {sums.get(r.id) or re_.summary}"
            A(line)
            if r.rel in ("copy_of", "version_of", "duplicate_of") and (CONTENT / f"{r.id}.json").exists():
                A(f"  Start from its accepted content `{CONTENT}/{r.id}.json` and change it as the entry and texture describe.")
        A("")
    # required facts
    planted = {x["entry"]["id"]: x for x in Mf.load_planted()}
    if file_id in planted:
        A("## Required facts (checked on submit)")
        for f in planted[file_id].get("facts", []):
            A(f"- {json.dumps(f, ensure_ascii=False)}")
        A("This file is a planted answer or distractor for a retrieval benchmark: it must be complete and correct, apart from any texture listed above.\n")
    # schema + exemplar
    A(f"## Content schema ({fam})\n```\n{schema_text(fam)}\n```")
    ex = EXEMPLARS / f"{fam}.json"
    if ex.exists():
        A(f"Exemplar (shape and tone only; a different firm and project): `{ex}`")
    A("Placeholders `{{PRJnnnn:key}}` work in any string. `table_ref` / `data_refs` render full tables from the numbers. "
      "Charts with `ref` plot those tables. Don't paste numeric results by hand.\n")
    A("## Prohibitions\n" + PROHIBITIONS)
    return "\n".join(out)
