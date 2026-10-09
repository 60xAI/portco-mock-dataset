# Stage 5 brief: folder tree and file list for one unit

You are writing the file list (manifest) for ONE unit of a fictional mock document archive: one acquired firm (A-G) or the group head office (HO). The archive belongs to a fictional drug-discovery and analytical services group built from acquisitions. Other agents later write each file's content from your entry, so every entry must be specific and consistent with the world. You write YAML only; no documents.

Your unit is given in the task message (`UNIT`). Repo: `/Users/kertlaansalu/projects/portco-mock-dataset` (git, branch `main`). Run all commands from the repo root.

## Read first

- `docs/spec-DEV-1370.md`: sections "File list (manifest)", "Folder tree", "Unfinished work and texture", "Planted answers".
- `world/group.yaml` and `world/firms.yaml`: your unit's record is your style guide (naming style, ID formats, date conventions, templates and their date ranges, terminology, voice, history). HO uses `group.share_root` and the group template.
- `world/projects.yaml`: your unit's projects (status, dates, client variant, lead, team, assays). `world/people.yaml`: who worked there and when. `world/clients.yaml`: client names per firm and period. `world/assays.yaml`: assay house names.
- `src/mockgen/manifest.py`: the `Entry` schema, allowed values (`DOC_TYPES`, `FORMATS`, `FINISH`, `MESS`, `TIERS`, `RELS`) and every validation rule. Your quotas are in `QUOTA[UNIT]`.
- Planted entries for your unit: `uv run mockgen manifest planted --firm UNIT`.

## Output

`manifest/UNIT.yaml` with a top-level `files:` list of `Entry` records.

- **Planted entries**: copy every planted entry for your unit verbatim (all fields, including id `Pnn`, dates, author, template, tags, related, tier), replacing only `path` and `filename` (follow `filename_hint` and your firm's naming style). Don't add planted tags to any other entry.
- **Your entries**: ids `UNIT-001`, `UNIT-002`, … (HO uses `HO-001`). Fill the quota so that per-bucket counts (planted included) match `QUOTA[UNIT]`: `deck` (pptx+ppt), `wb` (xlsx+xls), `pdf`, `word` (docx+doc), `catalogue` (one service catalogue for A-G, any format), `junk`, `csv` (HO only, already planted), plus the sub-counts `ppt`, `xls`, `doc` (legacy binary formats, mostly from before ~2008), `scan` (pdf_kind scan) and `export` (pdf_kind export). Small deviations are OK; the validator allows a margin.

## What makes a good file list

- **Folder tree**: SharePoint-like, 3-7 folder levels. The first segment is your share root (`firms.yaml` `share_root`, or `group.share_root` for HO). Typical subfolders: clients/projects (by client code or project id), proposals by year, QA/SOPs, templates, marketing, scans, finance/admin, people's personal folders. Use your firm's naming style: its case, separators and ID formats. Firm G keeps its own root and its own style (`root: heldback`).
- **Leavers' folders** (units A-F only): for 1-2 people from your unit who have left, add 2-5 files under `Archive/Users/<username>_old_laptop/...`, created while they were employed (`root: archive`, `mess: [leaver_folder, ...]`). For unit B, one of them must be the person with role_hint `leaver_old_laptop` (about 5 files: old decks, a workbook, notes).
- **Projects drive most files.** A completed project leaves a proposal/quote, maybe a statement of work, a results workbook or tracker, a readout deck, a report. In-progress projects have interim results and no final report. On-hold/cancelled projects stop partway (no final report). Lost/unanswered proposals have only a quote. Spread files over the firm's whole era, with more in recent years. Not every project needs files.
- **Other files**: SOPs, capability and training decks, price lists, trackers, QA documents, marketing, templates, the service catalogue, board or management packs (HO), integration documents (HO: integration programme charter, half-finished price harmonisation workbook, brand guidelines, org chart, board pack extracts, LIMS consolidation plan, SharePoint migration tracker, cross-sell plans).
- **Texture**: about 10-15% unfinished (`finish`: draft/interim/abandoned/empty_template), ~5% near-empty junk (`doc_type: junk`, e.g. `Presentation1.pptx`, `Book1.xlsx`, `Scan_0043.pdf`, `~$` names are NOT allowed), version mess (`_v3_FINAL_final`, `(2)`), `Copy of …` files, a deck duplicated from another firm (`mess: [duplicate_across_firms]`, describe the source in `summary`), unhelpful names. Use `mess` flags from `MESS` to tell writers what texture to add (tracked_changes, comments, tbc_placeholders, mixed_units, inconsistent_dates, typo, half_filled, draft_mark, stale_template…).
- **Scans** (`format: pdf`, `pdf_kind: scan`): old signed proposals, QA certificates, faxed client letters, signed protocol pages, handwritten-annotated reports. Never planted.
- **Exports** (`pdf_kind: export`, `tier: script`): a PDF export of one of your decks or Word files; `related: [{id: <source id>, rel: export_of}]`; dated on or after the source's `modified`.
- **People and dates**: `author` and `last_saved_by` are person ids employed at your unit (any unit for HO staff on HO files) on `created` and `modified` respectively. Usually the lead, a team member, BD or QA. Dates are ISO datetimes in working hours (`2014-03-06T10:41:00`), `created <= modified <= 2026-10-08`, inside the firm's era. `year` = created year. `template` = the firm template whose date range covers `created` (or the group template for HO), and `era` = that template's kind. `stale_template` is allowed for deliberate exceptions.
- **Clients**: `client_id` and `client_variant` = the name that firm used then (from `world/clients.yaml` / the project's `client_variant`).
- **Tier** (who writes the content): `sol` = science files (study/client reports, readout decks, proposals with prices, SOPs, capability decks, service catalogue); `haiku` = admin/HR/finance documents, trackers, price lists, results workbooks, memos, older copies and superseded versions of Sol-written files; `haiku_low` = junk files; `script` = exports and CSVs. Planted entries keep `orchestrator`/`script`.
- **`summary`**: one specific sentence telling the writer what the file is and what's in it (project id, client variant, assay house names, key point, state). **`target_length`**: e.g. `12 slides`, `3 sheets`, `8 pages`.
- Use `related` for version chains (`version_of` pointing at the newer/final file), `copy_of`, `proposal_for`, `report_for`, `results_for`, `export_of`. Related ids must be from your own unit or planted ids.
- **Never** mention cryo-EM. No real company, vendor or person names (see `config/blocklist.yaml`).

## Validate and finish

1. `uv run mockgen manifest validate --firm UNIT` must report 0 errors (warnings OK). Fix and re-run until clean.
2. `uv run mockgen manifest tree --firm UNIT` prints your tree. Glance at it for realism.
3. Commit and push only your file: `uv run mockgen commit --path manifest/UNIT.yaml -m "Stage 5: manifest UNIT"`. On push failure, follow `briefs/orchestration.md`.
4. Don't edit other units' files, `world/`, `src/`, `docs/` or `config/`. Don't write tests, review code or invoke any skills; generate and validate only.

## Reply

Briefly: entry count by bucket (deck/wb/pdf/word/catalogue/junk + ppt/xls/doc/scan/export), the top two levels of your tree, the leaver folders you created, and any validator rule you had to work around.
