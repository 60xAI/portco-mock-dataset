# Spec: reusable mock document archive for the buy-and-build portco demo

Copied from Linear [DEV-1370](https://linear.app/60x/issue/DEV-1370/spec-reusable-mock-document-archive-for-the-buy-and-build-portco-demo) on 2026-10-08. Parent: [DEV-1369](https://linear.app/60x/issue/DEV-1369/demo-video-mock-dataset-knowledge-retrieval-for-a-buy-and-build-portco).
Overrides from the build brief (2026-10-08) are listed in `docs/decisions.md`: no test suite (the "Testing Decisions" section is not implemented), and the repo is pushed to a private GitHub repo.

---

Implementation spec for the dataset half of DEV-1369. It was agreed with Kert on 2026-10-08 in a design interview. The video, ingestion and product changes are out of scope.

## Problem Statement

We need to show a PE operating partner that AI Brain can find knowledge buried in a portfolio company built from several acquisitions. We can't use real client data. Today we have no realistic archive to demo on, and none to measure retrieval quality against.

* The only synthetic data we have is the platform's local fixture. It writes markdown chunks straight into the database, so there are no real PowerPoint, Excel, Word or PDF files to upload, open or cite.
* A plausible demo archive needs more than a folder of generated text. It needs:
  * 30 years of mixed file formats
  * each acquired firm writing in its own style
  * departed employees' folders, version mess and unfinished work in progress
  * the same project appearing consistently across proposal, tracker, results workbook, report and LIMS export
  * assay numbers that look real to a scientist
* The fictional names in DEV-1369 clash with real organisations and a real person:
  * "Halden": HP Halden Pharma AS and Halden Bio
  * "Northgate Pharma": a real US company with that exact name; also a Kenyan distributor and Northgate Capital
  * "NGP Ltd": a UK energy consultancy and NGP Energy Capital
  * "Jim Thompson": COO and co-founder of a real drug-discovery CRO
* The product has gaps the demo would hit. Only PDFs open at a cited page; there are no thumbnails, no merging of name variants, no near-duplicate detection, no sheet names in citations, and manual upload flattens folders. The dataset has to work around these where a real archive plausibly would.

## Solution

A reusable mock archive with a generator behind it, kept in its own local git repo (`portco-mock-dataset` in Kert's projects folder, not pushed).

The archive is a fictional drug-discovery and analytical services group: a holding company formed from 6 acquired firms (A–F), plus a 7th firm (G, toxicology) held back to demo "ingest a newly acquired firm".

How it's built:

1. AI agents run from T3 Code create a coherent fictional world, then the folder tree and the list of files each firm holds.
2. A script generates all assay numbers.
3. Content subagents (Sol 6.1 and Haiku 5.5) each receive a self-contained "context pack" and return structured JSON content.
4. A shared renderer turns that JSON into real .pptx/.ppt, .xlsx/.xls, .docx/.doc, .pdf (including scanned and exported PDFs) and .csv files. Each firm gets its own template, the formatting of its era, and realistic document properties.
5. A validator rejects anything with real names, numbers that contradict the world, missing planted answers, or impossible dates.

The output:

* **At most 350 files** in a SharePoint-like folder tree. Firm G's archive sits in a separate root so it can be uploaded later.
* A `golden_set.json` listing, for each of the 5 demo queries, the correct answers and the distractors, down to file and slide, page or sheet. This makes the dataset reusable as a retrieval benchmark.

## User Stories

### Demo presenter and audience

1. As the demo presenter, I want an archive that looks like a real buy-and-build portco's shared drives, so that a PE operating partner recognises their own portfolio's mess.
2. As the demo presenter, I want every name in the archive to be fictional and screened against real companies and people, so that nothing embarrassing or legally risky shows on screen.
3. As the demo presenter, I want 8–10 decks containing a "bioinformatics for drug discovery" slide, so that query 1 has one clear best recent answer from firm D, 2 good alternatives, and realistic distractors.
4. As the demo presenter, I want an outdated version, a near-duplicate with a typo, and a generic slide in an unrelated deck among those 8–10 decks, so that ranking the best answer looks impressive.
5. As the demo presenter, I want the best bioinformatics deck to also exist as a PDF export, so that its citation opens at the exact page in today's product.
6. As the demo presenter, I want 4 past projects across firms B and C from different years matching "hERG and CYP inhibition screening on ~40 compounds from a kinase series, turnaround under 3 weeks". Each needs a results workbook with a benchmark table, a proposal stating price and turnaround, and a report. That way query 2 returns rich, comparable evidence.
7. As the demo presenter, I want query 2's distractors to be a hERG-only project, a CYP study on a different chemotype, and the right client with the wrong assay, so that precision is visible.
8. As the demo presenter, I want the benchmark tables also summarised inside the PDF reports, so that answers can cite a page even though spreadsheet citations lack sheet names.
9. As the demo presenter, I want the staff directory to show who ran each project and whether they've left, so that query 2 can say who to ask.
10. As the demo presenter, I want one client who bought from firms A, C and E under 3 name variants, and never from D or F, so that query 3 (cross-sell) shows the white space.
11. As the demo presenter, I want a different client with a similar name, so that query 3 has a realistic trap.
12. As the demo presenter, I want some documents to name two client variants side by side (for example "X Ltd (formerly …)" or a group client list with aliases), so that retrieval can link variants even though the product doesn't merge them.
13. As the demo presenter, I want firm G's held-back archive to add 2 more matching projects and a 4th variant of the same client name, so that query 4 shows newly acquired knowledge appearing.
14. As the demo presenter, I want no content about cryo-EM, and 1–2 structural biology mentions, so that query 5 shows an honest "no evidence" answer with the closest related work.
15. As the operating partner watching, I want old .ppt/.xls/.doc files and scanned PDFs among modern files, so that I believe the tool copes with 30 years of real archives.

### Realism

16. As a viewer, I want each legacy firm to have its own top-level share, naming style, templates, terminology and date conventions, so that it reads as several companies rather than one generator.
17. As a viewer, I want a group head-office share with integration files (integration programme, half-finished price harmonisation, cross-sell deck, brand guidelines, org chart, board pack extracts), so that it reads as one group built from acquisitions.
18. As a viewer, I want old files to keep the legacy brand, and newer files to show "Firm B, a [Group] company" and the group template, so that the acquisition history is visible.
19. As a viewer, I want leavers' folders such as `Archive/Users/<username>_old_laptop`, so that the "knowledge walked out the door" story is real.
20. As a viewer, I want version mess (`v3_FINAL_final`), "Copy of" files, decks duplicated across firms, and unhelpful names (`Presentation1.pptx`, `Scan_0043.pdf`), so that the archive feels human-made.
21. As a viewer, I want about 10–15% of files unfinished because their project is in progress or on hold, so that the archive looks like a working company rather than a museum.
22. As a viewer, I want realistic texture: reviewer comments, tracked changes, `[TBC]` placeholders, half-filled trackers, typos, mixed units and inconsistent date formats, so that files look human-made.
23. As a scientist viewer, I want assay values with realistic distributions, structure–activity trends, replicates, censored values (">30 µM") and QC flags, so that the data survives a close look.
24. As a scientist viewer, I want correct study designs and reporting conventions (hERG, CYP DDI, metabolic stability, stability testing, GLP tox), so that reports and SOPs read like the real thing.
25. As a viewer, I want charts and molecule drawings in decks and reports (dose–response curves, stability plots, chromatograms, compound grids), so that slides look like real slides.
26. As a viewer, I want author, last-saved-by and created/modified dates in document properties to match the person and era, so that metadata is consistent wherever it surfaces.
27. As a viewer, I want project IDs formatted differently in the LIMS export and in filenames, and people referred to by name variants ("Dr X. Surname", "Firstname Surname", "xsurname"), so that the archive needs real entity resolution.

### Dataset builder (Kert)

28. As the builder, I want the world built once and stored as structured data, so that every file draws from the same facts and nothing contradicts.
29. As the builder, I want the assay numbers generated by a deterministic script, so that the same value appears in the workbook, the report and the proposal, and a rerun reproduces it.
30. As the builder, I want a review checkpoint after world creation (one-page world summary, folder tree, planted-answer list) before any content is written, so that structural mistakes are cheap to fix.
31. As the builder, I want a second checkpoint after the ~45 planted-answer files and a 10-file pilot pack are rendered, so that quality is proven before bulk generation.
32. As the builder, I want the pilot pack to cover every format, including legacy .ppt/.xls/.doc, a scan and a PDF export, so that format risk shows up early.
33. As the builder, I want to run all generation from T3 Code with my own subscriptions, using the model and effort level fixed for each task, so that cost stays at zero marginal spend and results are consistent.
34. As the builder, I want `mockgen next` to tell me exactly which T3 model setting to use for each batch, so that my subagent prompt never hard-codes models.
35. As the builder, I want `mockgen status` to show progress by stage, firm, type and state, so that I can resume after a crash.
36. As the builder, I want claims on files to expire, so that a dead subagent never blocks a file forever.
37. As the builder, I want regeneration to work per file, per firm or for everything, so that changing one planted answer doesn't mean redoing everything.
38. As the builder, I want the file total capped at 350 by the validator, so that scope can't creep.
39. As the builder, I want a datasheet describing how the dataset was made, its seed, the public data sources with attribution, and how to regenerate it, so that it's reusable by others.

### Agents

40. As a world-creation agent, I want a staged brief (group → firms and timeline → staff → clients and variants → projects → compounds), with a validation script between stages, so that I can't build on a broken earlier stage.
41. As a firm folder-and-file-list agent, I want the world core plus my firm's style guide and quotas, so that I can produce a realistic folder tree and file list without inventing new world facts.
42. As a content subagent, I want one context pack per file holding the file's entry, the firm's style and era, the project record and numbers, the people and their roles at the time, the client variant, summaries of related files, the facts I must state exactly, the content schema, one exemplar and a list of prohibitions, so that I can write a believable file in isolation.
43. As a content subagent, I want `mockgen submit` to tell me exactly why my JSON was rejected, so that I can fix it in one retry.
44. As a critique agent, I want the file's context pack plus the rendered text, so that I can judge scientific plausibility, firm voice and consistency against the world.

### Future users

45. As a benchmark runner, I want `golden_set.json` with page and slide numbers counted the same way AI Brain's parser counts them, so that a top-3 check can be automated after upload.
46. As a product engineer, I want the archive to include the cases our product handles badly today (Office citations, name variants, near-duplicates, scans), so that it doubles as a test set when those gaps get fixed.

## Implementation Decisions

### Repository and tooling

* Standalone local git repo `portco-mock-dataset` in Kert's projects folder. Not pushed; pushing is Kert's later call.
* Python is managed with uv inside the repo. Libraries: python-pptx, openpyxl, python-docx, reportlab, pypdf, Pillow and pdf2image, matplotlib, RDKit, scikit-learn, Faker, pydantic, PyYAML, and `unstructured` (used only to compute golden page and slide numbers the way AI Brain does).
* System tools via Homebrew: LibreOffice (headless) for legacy binary formats and PDF exports, Tesseract and poppler for checking scans.
* The repo holds the generator, the world data, the manifest, the content JSON and the rendered output. The archive root and firm G's held-back root are siblings, so an upload of the main archive never includes G.

### Names

* The ticket's names are replaced; the planted structure stays.
* New names copy real naming patterns without being derived from any specific real company: founder surnames, place names, "X Discovery", "X Biosciences", "X Analytical". Parody look-alikes of real companies are not allowed.
* A Sol agent with web search screens the group, the 7 legacy firms, about 15 main clients and about 10 named staff. It checks company registries, OpenCorporates, SEC filings, LinkedIn and the web, and records how each name was checked and the result.
* The other ~55 clients get an exact-name search. Background staff come from Faker with a realistic mix of nationalities.
* A blocklist holds known collisions (Halden, Northgate, NGP, Jim Thompson) and a list of major real CRO and pharma names. The validator checks every proper name against it, exact and fuzzy.
* Already screened as safe, if wanted: groups Velmorwick, Kelmorwick, Ordelmere, Tarnovell, Fenlorwick; clients Avernelwick, Selverant, Corvenlea, Tervemere, Elvarmere. The proposal was Tarnovell Bioscience Group plus Corvenlea Pharma / Corvenlea Ltd / Corvenlea Pharmaceuticals plc / Corvenlea (US).

### The fictional world

One store of structured records, loaded and checked by one module. Entities:

* **Group:** name, head office, group template, integration programme.
* **Firm A–G:** legacy brand, service focus, founding and acquisition dates (acquisitions from about 1996 to 2024; G acquired "now", October 2026), head office location, naming style, ID formats, date conventions (UK or US), template history (legacy, then a transition, then the group template), terminology, and assay name variants.
* **Person:** canonical name, name variants, username, firm, role history with dates, joined and left dates, service line. The staff directory covers 150–250 people.
* **Client:** canonical name, variants with which firm used which variant and when, segment, location, and whether it's a planted lookalike. 60–80 clients.
* **Service line and assay catalogue:** canonical assays with per-firm variant names, for example "hERG patch clamp" / "hERG QPatch" / "IKr inhibition" and "CYP3A4 inhibition" / "3A4 DDI screen".
* **Compound series and compounds:** invented scaffolds, RDKit-enumerated analogues, SMILES, series ID, chemotype (kinase series and others).
* **Project:** per-firm ID plus the LIMS ID format, firm, client and the variant used, services and assays, compounds, lead scientist and team, dates (quote, start, interim, completion), status, price, turnaround, outcome, and which planted answer it supports, if any.
  * Status mix: about 65% completed, 15% in progress, 12% proposal sent but lost or unanswered, 8% on hold or cancelled.
* **Result sets:** produced by the numbers script, tied to the project and its compounds.

World "today" is October 2026. Every date in every file must sit inside the firm's lifetime and the people's employment windows.

### Assay numbers (script, no LLM)

* Endpoints:
  * hERG IC50
  * CYP1A2/2C9/2C19/2D6/3A4 percent inhibition at 10 µM, and IC50
  * kinase IC50s
  * microsomal and hepatocyte intrinsic clearance, half-life
  * plasma protein binding, Caco-2 permeability, solubility
  * stability study assay and impurities at each timepoint and storage condition
  * formulation screens
  * in vitro and in vivo tox readouts for G: cytotoxicity, Ames, micronucleus, dose-range-finding observations
* Values are predicted for the invented compounds by simple models trained on public ADMET benchmark data, plus property-based trends, assay noise, replicates, censoring and QC flags. No public record is copied into the archive.
* If a public dataset is unavailable, parametric distributions with property-driven trends are an acceptable fallback.
* Output is deterministic for a given seed. Content agents receive the numbers and may not change them.

### File list (manifest)

One entry per file, at most 350. Each entry holds:

* file ID, path, filename, format, document type
* firm, year and era, created and modified dates
* author and last-saved-by
* project(s), client and the variant used
* finish state: final, draft, interim, superseded, abandoned or empty template
* mess flags
* which planted facts it carries
* related files: its version chain, the PDF export of a deck, the proposal behind a report
* writer tier (Sol, Haiku or the orchestrator thread)
* template, target length
* generation state

Document types:

* Decks: capability, pitch, results readout, training
* Workbooks: assay results, project tracker, price list
* PDFs: study report, client report
* Word: proposal or quote, SOP, statement of work
* Other: service catalogue, LIMS export, staff directory, client list, board pack extract, integration document, junk

Agreed split:

| Format | Count | Of which |
| -- | -- | -- |
| Decks | ~85 | ~8 legacy .ppt |
| Workbooks | ~85 | ~10 legacy .xls |
| PDFs | ~105 | ~15 scans, ~12 deck exports |
| Word | ~45 | ~4 legacy .doc |
| CSV | 3 |  |
| Service catalogues | 7 |  |
| Junk / "Copy of" | ~20 |  |

Firm G gets about 35 files. The group head office gets about 20 integration files from within the total. About 45 files are planted answers or distractors.

### Folder tree

* SharePoint-like: one top-level share per legacy firm in that firm's naming style, a group head-office share, and an archive area with leavers' folders.
* Typical subfolders: clients and projects, proposals by year, QA/SOPs, templates, marketing, scans.
* Depth of 3–7 levels. Duplicated decks across firms and unhelpful filenames as in the ticket.

### Style guides

One per firm and era, plus the group template. Each covers:

* voice and terminology, assay variant names
* date format and units
* ID and filename conventions, typical lengths
* template colours and fonts (legacy brand as text, no real logos)
* the transition rules after acquisition

### Planted answers (golden set)

The five ticket queries keep their structure with the new names:

**Query 1: bioinformatics slide.**

* Correct: the best recent slide from firm D (group template, ~2025) plus 2 good alternatives, such as an older D capability deck and a head-office cross-sell deck reusing the slide.
* Distractors: an old outdated D version (.ppt), a "Copy of" near-duplicate with a typo, and a generic slide in an unrelated deck from firm A.
* The best deck also exists as a PDF export.

**Query 2: hERG + CYP on a kinase series.**

* Correct: 4 projects across B and C from different years. Each has ~40 compounds from a kinase series and a turnaround of 3 weeks or less, plus a proposal with price and turnaround, a results workbook with a benchmark table, and a PDF report that also summarises the table.
* Distractors: a hERG-only project, a CYP study on a different chemotype, and the right client with the wrong assay.
* Lead scientists are in the staff directory with leaving dates where relevant.

**Query 3: cross-sell.**

* Correct: one client buying from A, C and E under 3 variants and never from D or F.
* Distractor: a client with a similar name.
* Bridging documents in the head-office share and proposals name variants together.

**Query 4: newly acquired firm.**

* G's held-back archive holds 2 more matching projects and the client's 4th variant.

**Query 5: cryo-EM.**

* No cryo-EM content anywhere.
* 1–2 structural biology mentions, such as crystallography-based docking in D or a structural biology collaboration in A.

The golden set file lists, per query: the query text, the expected answers (path, slide/page/sheet, the fact), the distractors, the closest related work for query 5, and whether it depends on firm G. Slide and page numbers are computed by partitioning the rendered files with `unstructured`, matching how AI Brain numbers them.

### Unfinished work and texture

* About 10–15% of files are unfinished, driven by project status:
  * in-progress projects have interim results and no final report
  * on-hold projects stop partway
  * lost proposals have only a quote
* Texture, applied in proportion: "DRAFT" marks, `[TBC]` and `XX%` placeholders, empty template sections, half-filled trackers, reviewer comments, tracked changes, stale v2/v3 copies, typos, mixed units, inconsistent date formats, "Copy of …" files.
* About 5% are near-empty junk files.
* Strict rule: files holding a correct planted answer are complete and correct. Drafts, outdated versions and typo copies are used only as distractors.

### Content JSON (one schema per family, validated on submit)

* **Deck:** slides, each with layout, title, nested bullets, speaker notes, table, chart reference (to numbers), image reference (molecule grid or chart), footer. Plus template ID.
* **Workbook:** sheets, each with name, cell grid (values and formulas), merged ranges, number formats, column widths, hidden flag, cell comments, deliberately blank or partial rows.
* **Document (Word and PDF report):** header and footer, title block, sections (heading, paragraphs, lists, tables), signature block, appendices, tracked changes, comments, watermark.
* **CSV:** columns and rows (LIMS, staff directory, client list), generated by script from the world.
* **Scan:** the source document content plus scan settings (skew, noise, blur, stamp or handwritten annotation text, page count).

### Renderer

* Turns content JSON, the style guide and the template into the target file.
* Then:
  * sets document properties (author, last saved by, created, modified, company, title) and filesystem dates
  * converts legacy formats through headless LibreOffice
  * exports selected decks to PDF through LibreOffice
  * produces scans: render to PDF, rasterise at about 200 dpi, greyscale, skew within ±1.5°, noise and blur, optional stamp, rebuild as an image-only PDF
* Charts come from matplotlib using world numbers; molecule images come from RDKit.
* Rendering is deterministic, and re-rendering never calls a model.

### Validator (runs on every submit and on the whole archive)

* **Content:** schema validity; blocklist and registry name check; every tagged number matches the world.
* **Planted answers:** each required fact is present at the stated place.
* **Names and dates:** client and assay variants match the firm and era; dates fall inside the firm's lifetime and the people's employment.
* **Archive limits:** total files ≤ 350; each file under 30 MB (UI limit) and 60 MiB (ingestion limit).
* **Rendered files:**
  * every file reopens in its library, or LibreOffice for legacy formats
  * scans have no text layer, and Tesseract recovers a minimum word count from them
  * golden page and slide indices agree with `unstructured`

### `mockgen` command-line tool (the interface for agents and Kert)

* `mockgen world validate` and `mockgen manifest validate`: check the stage outputs.
* `mockgen numbers`: generate the result sets.
* `mockgen next --tier sol|haiku [--firm X] [--type T] [--batch N]`: claim a batch of 5–8 files, same firm and type preferred. Prints the file IDs and the exact T3 model setting for the batch.
* `mockgen pack <file-id>`: print the context pack, about 8k tokens or less.
* `mockgen submit <file-id> <content.json>`: validate, then render and accept, or reject with numbered reasons.
* `mockgen release <file-id>`: free a claim. Claims also expire automatically after a timeout.
* `mockgen render [--file|--firm|--all]`
* `mockgen status`: progress by stage, firm, type and state.
* `mockgen validate --all`
* `mockgen golden`: build the golden set.
* `mockgen export`: archive root plus G's root, with a manifest listing.
* Claims and state live in a local store with file locking, so parallel subagents never double-claim.

### Context pack contents

* the file's manifest entry
* the firm's style guide and era conventions
* the project record and its numbers slice
* the people involved and their roles at the time
* the client variant
* summaries of related files (stored when each file is accepted)
* required exact facts
* the content schema
* one exemplar of the same document type
* prohibitions: no real names, no new numbers, no contradicting the world, nothing outside the file's era

### Models and T3 Code settings (fixed per task; kept in one model routing config that `mockgen next` reads)

| Task | Model and setting |
| -- | -- |
| Name generation and screening | Sol: `{"providerInstanceId":"codex","model":"gpt-6.1-sol","options":{"reasoningEffort":"medium"}}` |
| World core, staged | Sol, medium |
| Folder tree and file list per firm and head office (parallel) | Sol, medium |
| Assay numbers | Script, no model |
| ~45 planted-answer files and the 10-file pilot | The orchestrating T3 thread (Claude Opus 5.5) |
| Science background files (reports, readouts, proposals with prices, SOPs, capability decks) | Sol, medium |
| Admin, HR and finance documents, tracker notes, older copies of Sol-written files | Haiku: `{"providerInstanceId":"claudeAgent","model":"claude-haiku-5-5","options":{"effort":"medium"}}` |
| Junk files, filenames, document properties | Haiku, `"effort":"low"` |
| Critique: all planted-answer files plus 1 in 5 Haiku files | Sol, medium |

T3 usage rules:

* Delegate through `delegate_task` with self-contained briefs: absolute paths, and the agent runs `mockgen pack` itself.
* Full-access runtime so agents can run `mockgen`.
* At most 20 concurrent tasks.
* Stable request IDs per batch, such as `dev1369-content-B-07`, so retries never duplicate.

### Stages and checkpoints

1. Setup: repo, environment, tools.
2. Names, generated and screened.
3. World core, staged, validated by script after each stage.
4. Assay numbers.
5. Folder tree and file list for each firm and the head office; script check of planted-answer coverage and the 350 cap. **Checkpoint 1 (Kert).**
6. Planted-answer files and the 10-file pilot pack, with Sol critique. **Checkpoint 2 (Kert).**
7. Background content in batches via T3.
8. Critique sampling and fixes.
9. Full validation, golden set, export, datasheet.

### Working around product gaps (dataset-side only)

* PDF exports of key decks.
* Benchmark tables also summarised in PDF reports.
* Bridging documents that name client variants together.
* Folder paths kept in the output tree for connector-based upload later.

## Testing Decisions

*Not implemented in this build (see `docs/decisions.md`).* Original text kept for reference:

* One seam: the `mockgen` command-line tool. Tests drive it as agents and Kert do and check what comes out: the files, statuses and rejection reasons.
* A good test sets up a tiny fixture world (2 firms, 3 projects, about 6 manifest entries), runs CLI commands, and checks observable results (files reopen, text on the right slide/page/sheet, properties and dates set, legacy files open in LibreOffice, scans have no text layer and Tesseract recovers words).
* Rejection behaviour for a schema error, a blocklisted name, a number contradicting the world, a missing planted fact, a date outside someone's employment, a 351st file.
* Claims: concurrent `next` calls never return the same file; expired claims return to the pool; `release` frees a claim.
* Determinism: same seed, identical world, numbers and content JSON.
* Golden set indices equal what `unstructured` returns.
* Manual checks: both checkpoints are Kert's review. The full archive must pass `mockgen validate --all` before export.

## Out of Scope

* Recording the demo video.
* Uploading or ingesting into AI Brain, setting up a SharePoint/Drive tenant, and running the golden queries against the product. The golden set enables that later.
* Fixing product gaps: Office viewer at slide or page, thumbnails, name-variant merging, near-duplicate detection, sheet names in citations, folder upload, document metadata extraction.
* Paid APIs or external spend. Everything runs on Kert's subscriptions through T3 Code.
* Domain-expert review.
* Pushing the repo to GitHub.

## Further Notes

* **Public data:** ADMET benchmark data (for example the Therapeutics Data Commons sets derived from ChEMBL and PubChem) is used only to train value models applied to invented compounds. Records are not reproduced. The datasheet credits the sources; ChEMBL-derived data is CC BY-SA.
* **Product facts:** the gap facts come from reading the code on `development` on 2026-10-08; nothing was run:
  * Office citations fall back to download.
  * Slide numbers are stored as `page_number`.
  * Spreadsheet citations lack the sheet name.
  * Entities merge only on exact name or very high vector similarity.
  * Manual upload flattens paths to `uploads/<file>`.
  * Tesseract OCR is installed but untested on scans.
  * The UI file limit is 30 MB; the ingestion limit is 60 MiB.
* **Risks to watch:**
  * Haiku's JSON quality; mitigated by schema rejection and retry.
  * How faithfully LibreOffice converts legacy formats; the pilot catches it.
  * Whether OCR recovers text from scans; the pilot catches it, and scans never carry planted answers.
  * Voice sameness across firms; mitigated by style guides, critique and splitting work between Sol and Haiku.
* The parent ticket DEV-1369 has the decisions comment for Fergus. Product-gap decisions belong to him.
