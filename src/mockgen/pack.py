"""`mockgen pack <file-id>`: self-contained context pack for one file (~8k tokens max)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from . import manifest as Mf
from .paths import CONTENT, EXEMPLARS, NUMBERS, ROOT, STATE, WORLD, TODAY
from .schemas import schema_text
from .world import load_world


def preflight(file_id: str | None = None) -> list[str]:
    errors = []
    es = Mf.load_entries(errors)
    w = load_world(errors)
    if errors:
        return errors
    if file_id and file_id not in {e.id for e in es}:
        return [f"unknown file id {file_id}"]
    for e in es:
        if file_id and e.id != file_id:
            continue
        if e.doc_type in ("wb_pricelist", "service_catalogue"):
            from .prices import list_prices
            firms = [e.unit] if e.unit in w.firms else [k for k, f in w.firms.items() if f.joined_group and f.joined_group <= e.created.date()]
            if not firms or any(not list_prices(w, k, e.created.year) for k in firms):
                errors.append(f"{e.id}: required list prices missing")
        for pid in e.projects:
            p = w.projects.get(pid)
            if p is None:
                errors.append(f"{e.id}: unknown project {pid}")
                continue
            try:
                nd = json.loads((NUMBERS / f"{pid}.json").read_text())
                errors += [f"{e.id}/{pid}: {x}" for x in check_numbers(p, nd)]
            except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
                errors.append(f"{e.id}/{pid}: invalid or missing numbers: {exc}")
    return sorted(set(errors))


def check_numbers(p, nd) -> list[str]:
    errors = []
    values, tables = nd["values"], nd["tables"]
    for key, expected in (("project_id", p.id), ("firm", p.firm), ("status", p.status)):
        if nd.get(key) != expected:
            errors.append(f"{key} disagrees with world")
    price = f"{p.price.currency} {p.price.amount:,.0f}"
    if not p.price.amount or values.get("price") != price:
        errors.append("required prices missing or disagree with world")
    if values.get("n_compounds") != str(p.n_compounds):
        errors.append("compound count summary disagrees with world")
    for name, table in tables.items():
        if not table["columns"] or any(len(row) != len(table["columns"]) for row in table["rows"]):
            errors.append(f"{name}: row width disagrees with columns")
    if "stability" in p.assays and p.status in ("completed", "in_progress", "on_hold", "cancelled"):
        rows = tables.get("stability", {}).get("rows", [])
        if not rows or not p.dates.start:
            return errors + ["stability results or study start missing"]
        end = p.dates.completion or p.dates.interim or TODAY
        months = max(0, (end - p.dates.start).days // 30)
        if end < p.dates.start or any(float(row[1]) < 0 or float(row[1]) > months for row in rows):
            errors.append("stability table exceeds study cutoff")
        last = max(float(row[1]) for row in rows)
        if float(values.get("stability.last_timepoint_months", -1)) != last:
            errors.append("stability timepoint summary disagrees with table")
        t0 = [row for row in rows if float(row[1]) == 0]
        if not t0 or any(row[2:] != t0[0][2:] for row in t0) or values.get("stability.t0_assay") != t0[0][2]:
            errors.append("stability initial summary/conditions disagree with table")
    return errors


def source_snapshot(file_id: str) -> dict:
    entries = {e.id: e for e in Mf.load_entries([])}
    e = entries[file_id]
    files = list(WORLD.glob("*.yaml")) + [EXEMPLARS / f"{Mf.family(e)}.json"]
    files += list(NUMBERS.glob("*.json")) if e.unit == "HO" else [NUMBERS / f"{pid}.json" for pid in e.projects]
    if e.projects:
        files.append(NUMBERS / "compounds.json")
    files += [CONTENT / f"{r.id}.json" for r in e.related]
    inputs = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None for p in files}
    for name in ("pack.py", "prices.py", "schemas.py"):
        inputs[f"src/mockgen/{name}"] = hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
    inputs["entry"] = e.model_dump(mode="json")
    inputs["related_entries"] = {r.id: entries[r.id].model_dump(mode="json") for r in e.related if r.id in entries}
    inputs["required_facts"] = next((p for p in Mf.load_planted() if p["entry"]["id"] == file_id), None)
    blob = json.dumps(inputs, sort_keys=True, ensure_ascii=False).encode()
    return {"fingerprint": hashlib.sha256(blob).hexdigest(), "inputs": inputs}


def source_receipt(file_id: str):
    path = STATE / "packs" / f"{file_id}.json"
    return json.loads(path.read_text()) if path.exists() else None


def source_errors(file_id: str, fingerprint: str | None) -> list[str]:
    receipt = source_receipt(file_id)
    if receipt is None or not fingerprint:
        return ["source fingerprint missing; run mockgen pack and pass its --source fingerprint when submitting"]
    if fingerprint != receipt["fingerprint"] or fingerprint != source_snapshot(file_id)["fingerprint"]:
        return ["source changed since pack; obtain a new pack and re-review content, including prose, before submitting"]
    return preflight(file_id)


def changed_sources() -> list[str]:
    changed = []
    for e in Mf.load_entries([]):
        receipt = CONTENT / f"{e.id}.source.json"
        if not (CONTENT / f"{e.id}.json").exists() and not receipt.exists():
            continue
        if not receipt.exists():
            changed.append(f"{e.id}: untracked; content re-review required")
            continue
        try:
            saved = json.loads(receipt.read_text())
            current = source_snapshot(e.id)
            if saved["fingerprint"] != current["fingerprint"]:
                changed.append(f"{e.id}: changed; content re-review required")
        except (OSError, ValueError, KeyError, TypeError):
            changed.append(f"{e.id}: invalid fingerprint; content re-review required")
    return changed


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
    errors = preflight(file_id)
    if errors:
        raise ValueError("generation preflight failed:\n" + "\n".join(errors))
    snapshot = source_snapshot(file_id)
    es = {e.id: e for e in Mf.load_entries([])}
    if file_id not in es:
        return f"unknown file id {file_id}"
    e = es[file_id]
    w = load_world([])
    fam = Mf.family(e)
    out = []
    A = out.append
    A(f"# Context pack: {file_id}\n")
    A(f"Source fingerprint: `{snapshot['fingerprint']}`. Submit rejects a changed source. A new pack requires content re-review.\n")
    A(f"Write the content JSON for ONE file. Family: **{fam}**. Save it to `{CONTENT}/{file_id}.json`, then run from `{ROOT}`:\n"
      f"`uv run mockgen submit {file_id} content/{file_id}.json --source {snapshot['fingerprint']}`. On rejection, fix every numbered reason and resubmit (aim to pass in one retry).\n")
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

    if e.doc_type in ("wb_pricelist", "service_catalogue", "deck_capability"):
        from .prices import list_prices
        firms = [e.unit] if e.unit in w.firms else [L for L, f in w.firms.items() if f.joined_group and f.joined_group <= e.created.date()]
        A(f"## List prices ({e.created.year})")
        A("These are the firm's list prices for this year. Price lists and catalogues may quote them as written (they are world facts, not results); "
          "don't invent other prices. Columns: service, unit, price, currency, volume discount.")
        for L in firms:
            for row in list_prices(w, L, e.created.year):
                A(f"- {L}: {row}")
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
                    if 0 < len(t['rows']) <= 12:
                        A(f"- `{pj}:{k}`: {t['title']}; {len(t['rows'])} rows (all shown, so you can describe trends; still embed via table_ref); columns {t['columns']}")
                        for row in t['rows']:
                            A(f"    {row}")
                    else:
                        A(f"- `{pj}:{k}`: {t['title']}; {len(t['rows'])} rows (table_ref renders all of them); columns {t['columns']}; first row {t['rows'][0] if t['rows'] else '-'}")
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
        sums = {}
        for r in e.related:
            cp = CONTENT / f"{r.id}.json"
            if cp.exists():
                sums[r.id] = json.loads(cp.read_text()).get("summary")
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
    if source_snapshot(file_id)["fingerprint"] != snapshot["fingerprint"]:
        raise ValueError("source changed while building pack; retry after source edits stop")
    receipt = STATE / "packs" / f"{file_id}.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n")
    return "\n".join(out)
