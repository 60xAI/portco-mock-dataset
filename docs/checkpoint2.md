# Checkpoint 2: planted answers and pilot pack

53 files are written, rendered and accepted by `mockgen submit`: 43 planted answers and distractors (P01-P43) and the 10-file pilot pack. Rendered output is in `output/archive/` and `output/heldback_firm_G/`; content JSON is in `content/`; the critique files are in `critique/`.

## Files to open

| What | Path |
|---|---|
| Q1 best deck (slide 3) and its PDF export (page 3) | `output/archive/QuenverellData/marketing/capabilities/2025/quenverell-capabilities-bioinformatics-2025.pptx` / `.pdf` |
| Q1 distractors: typo copy, v2 draft, 2012 .ppt | same folder: `Copy of …pptx`, `…_v2_DRAFT.pptx`; `…/capabilities/2012/quenverell-bioinformatics-2012.ppt` |
| Q1 + Q3: head-office cross-sell deck | `output/archive/Tarnovell_Group/Commercial/Cross_Sell/2026/One_Tarnovell_Services_Cross_Sell_2026-06.pptx` |
| Q2: one complete project (2011, .doc quote, workbook, report) | `output/archive/BrindlewytheData/Studies/2011/BW11_0275/` |
| Q2: Merrivoss 2024 project | `output/archive/MerrivossData/Client_Work/TP04/MV-2024-358/` |
| Q3: client identity bridge, white-space matrix | `output/archive/Tarnovell_Group/Integration/Client_Identity/2026/Client_Identity_Bridge_v3_2026-08.xlsx`, `…/Commercial/Cross_Sell/2026/Cross_Sell_White_Space_Matrix_DRAFT_v2.xlsx` |
| Q3: CSV exports (staff, LIMS, CRM) | `output/archive/Tarnovell_Group/People/Directory/2026/`, `…/Integration/LIMS/Exports/2026/`, `…/Commercial/CRM/Exports/2026/` |
| Q4: firm G held-back project for 'Corvenlea (US)' | `output/heldback_firm_G/OsterquillData/Studies/OT-20-S0178/` |
| Q5: closest related work | `output/archive/QuenverellData/engagements/qv.25.086/deliverables/drelvessa-qv.25.086-docking-report-v1.pdf`, `output/archive/VellacombeData/Clients/RI/VD-18-131/Readouts/RI13_route_readout_24Jan19.pptx` |
| Pilot: scan | `output/archive/WestravelleData/Stability/EP19/WA-2011-192/Scans/Signed/EP19_L02_06M_SIGNED_ANNOTATED.pdf` |
| Pilot: legacy .ppt / .xls / .doc | `output/archive/VellacombeData/Clients/EB05/VD-96-072/Readouts/EB05_RteA_13Feb97.ppt`, `output/archive/Archive/Users/mellerscombe_old_laptop/Bench/Plate_maps/plate_capacity_211106_me.xls`, `output/archive/MerrivossData/Proposals/2006/NM08/MV-2006-090_Quote_052206_R1.doc` |
| Pilot: pptx + PDF export | `output/archive/BrindlewytheData/Studies/2025/BW25_0600/Readouts/BW25_0600_CLIENT.pptx` / `BW25_0600_CLIENT_export.pdf` |
| Golden set (trial build) | `output/golden_set.json` |

## Format checks

- Legacy formats: all six .ppt/.xls/.doc files reopen in LibreOffice (converted from the rendered OOXML files).
- PDF exports: P02 (14 pages) and B-046 (9 pages) export cleanly with a text layer. Q1's slide 3 is page 3 in the export, matching `unstructured`.
- Scan: E-037 is image-only (no text layer). Tesseract recovers 276 words across 2 pages.

## What the critique changed

Sol reviewed all 53 files. Most verdicts were `fix`; all fixes were applied and every file was re-submitted and accepted.

- **Numbers generator:** one consistent hERG censoring rule (geometric mean of finite cell IC50s when they are the majority, otherwise >30 µM; precipitation-limited compounds reported as >10 µM); CYP positive-control historical means and 0.5-2× acceptance; one CYP3A4 IC50 probe; PPB "fu" column relabelled "Unbound (%)"; stability "Complies" now follows a specification with limits for each specified impurity; formulation appearance now consistent with solubility at the 10 mg/mL loading.
- **Q2/Q4 documents:** future tense in proposals; US spelling for the US firms; real job titles instead of "Study Director"; steady-state rule for hERG exposure; CYP control procedures with furafylline/ticlopidine preincubation; CYP3A4 IC50 scope matching the price; assay-specific conclusions (the hERG-only and DMPK distractors no longer mention CYP); deviations section for rejected runs and precipitation; Osterquill non-GLP status in workbooks.
- **Q1 decks:** invented case-study counts removed; more careful wording on target validation and biomarkers; volcano-plot and RNA-seq explanations corrected; the 2012 deck no longer contains a note referring to 2014.
- **Pilot pack:** B-008 now names the selected compound (AP02-01430) and its tie-break; A-001 route story matches the structures and shows all 24 compounds; C-037, E-037, E-046, G-026 and F-019 expanded to realistic depth with corrected science (reporting bounds, no-NADPH controls, impurity specs, control validity, provisional vehicle).
- **Q3/Q5:** P32 binding units and clearance claims corrected; P36 donor design made estimable, and Corvenlith is now an existing client; P34 no longer treats the October acquisition as complete in August; P42/P43 gain provenance and identifiers.
- **CSVs:** exports contain only events up to their snapshot date; the LIMS export has a source date-format column; staff line managers form a coherent hierarchy; some CRM owners are filled in.
- **Renderer:** handwritten-style signature images, a faint uneven scan stamp, margin notes that don't cover text, headings and short tables kept together, plain tables and monochrome structures for pre-2007 files, auto column widths and landscape fit-to-width for workbooks, log scale for wide-range bar charts.

Not changed: the target lengths of some reports remain shorter than the manifest's `target_length`. Screening reports of 5-8 pages are realistic, and the critique's requests to add invented detail (run identifiers, extra pages of protocol) were applied only where the information exists in the world.

## Stage 7 brief

See below; it is also in `briefs/stage7-content.md` (the per-batch child brief).

Remaining: 287 files (Sol 153, Haiku medium 104, Haiku low 20, script 10 exports, which render automatically when their source is accepted).

### Starting another generation run

The counts and review results above describe the original run. For the next run, follow `briefs/orchestration.md` and `config/models.yaml`. The parent-written format pilot does not qualify as a writer-tier pilot. Each writer tier must pass its own critiqued pilot before bulk dispatch, and cheap-tier files receive full review.

```text
Run background generation using briefs/orchestration.md. Freeze and preflight the sources,
pilot every writer tier using its own target, record the original critique verdicts and
promotion decision, then dispatch only passing tiers. Writers follow briefs/stage7-content.md
and submit with the source fingerprint printed by their pack. Use mockgen commit and
mockgen sync for all Git changes, with exact paths for critique and orchestration artifacts.
```
