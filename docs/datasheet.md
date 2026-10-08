# Datasheet: portco-mock-dataset

A fictional document archive of a drug-discovery and analytical services group, **Tarnovell Bioscience Group**, built from seven acquired firms over 30 years. It was made to demo AI Brain on buy-and-build portfolio companies (DEV-1369, DEV-1370). Everything in it is invented: firms, people, clients, compounds, projects and results.

## Contents

| | Count |
|---|---|
| Files | 340 (cap 350) |
| Main archive (`output/archive/`) | 306 files, firms A-F and the head office |
| Held-back firm G (`output/heldback_firm_G/`) | 34 files, for the "acquisition closes" demo step (query 4) |
| Formats | 112 PDF (85 native, 15 scans, 12 deck exports), 82 .pptx, 8 .ppt, 80 .xlsx, 10 .xls, 41 .docx, 4 .doc, 3 .csv |
| Firms | A Vellacombe Discovery (Nottingham, medicinal chemistry), B Brindlewythe Biosciences (Cambridge, in vitro biology), C Merrivoss Bioanalysis (Madison US, DMPK), D Quenverell Computational (Edinburgh, bioinformatics), E Westravelle Analytical (York, stability), F Durnesswick Laboratories (Durham US, formulation), G Osterquill Toxicology (Portland US, held back) |
| World | 200 people with employment windows and role history, 70 clients with name variants over time, 130 projects, 20 compound series (1,280 enumerated compounds) |

The folder tree mirrors each firm's legacy shared drive (`docs/tree.txt`). Files carry realistic document properties (author, company, application version, created and modified dates) and file modification times.

## Demo queries and the golden set

`output/golden_set.json` lists, for each of the five demo queries, the expected files, distractors, supporting files and (for query 5) the closest related work, with the page or slide where each answer sits:

1. A slide explaining bioinformatics for drug discovery (best deck plus its PDF export; typo copy, draft and 2012 .ppt distractors).
2. hERG and CYP inhibition on ~40 compounds from a kinase series, turnaround under 3 weeks (4 projects at firms B and C, each with proposal, results workbook and report; 3 distractor projects).
3. The full history of client Corvenlea across the legacy firms, and the service lines it has never bought (client name variants, a client identity bridge and a white-space matrix).
4. Query 2 again after firm G's archive is ingested (2 more matching projects at G).
5. "Have we done any cryo-EM work?" The archive contains none; the closest related work is two structural-biology-guided projects.

Locators: `answer_page_number` gives the pages carrying the most planted facts (pptx: slide index; pdf: page; xlsx: sheet index, with sheet names in `sheet`). `.docx` and `.doc` files have no page numbers in `unstructured`, so they are located by `answer_section` (the nearest heading). `unstructured_page_number` lists every page that mentions a fact.

## How it was made

1. **Names** were invented and screened against web search results for real companies, CROs, pharma and people. Registry checks were web-index searches, not direct registry queries (`names/screening.yaml`). Known collisions (Halden, Northgate, NGP, Jim Thompson) are blocklisted (`config/blocklist.yaml`).
2. **World** (`world/*.yaml`): group, firms, templates and eras, people, clients, projects, compound series and assays. It went through a realism pass and is checked by `mockgen world validate`.
3. **Numbers** (`numbers/*.json`) are generated deterministically from the world with seed **1369**. Compounds are enumerated with RDKit from each series' core and substituents. Assay values come from simple RandomForest models trained on public ADMET benchmarks (below), with CYP outputs rank-calibrated to realistic hit rates. Stability, method validation, formulation and toxicology results are parametric. Writers never type results: content uses `{{PRJnnnn:key}}` placeholders and table references that the renderer fills in.
4. **Manifest** (`manifest/*.yaml`): 340 entries with path, format, author, dates, finish state, texture (drafts, comments, tracked changes, typos, half-filled sheets, leaver folders), related files and the writer tier.
5. **Content** (`content/*.json`): 48 planted and pilot files were written by the orchestrator; 153 by GPT-6.1 Sol (medium effort); 104 by Claude Haiku 5.5 (medium); 20 junk files by Claude Haiku 5.5 (low); 15 exports, CSVs and script files by code. All runs used the builder's own subscriptions in T3 Code (no paid API spend).
6. **Rendering** (`mockgen render`): python-pptx, openpyxl and python-docx for OOXML; headless LibreOffice for legacy .ppt/.xls/.doc and PDF; scans are rasterised, skewed, noised and stamped into image-only PDFs. Charts use matplotlib and molecule grids use RDKit. Rendering is deterministic and never calls a model.
7. **Checks** (`mockgen submit`, `mockgen validate --all`): schema, blocklisted or unregistered names, numbers matching the world, planted facts present, dates inside employment windows, era rules (no group brand before 2020, no client name before it was in use, no firm G variant outside G), no cryo-EM, no writer commentary, the 350-file cap, and each file reopening (OCR for scans).
8. **Review**: GPT-6.1 Sol critiqued every planted and pilot file, and the fixes were applied. The first two samples of Haiku-written files needed fixes in 16 of 20 cases, so Sol then reviewed and fixed every Haiku-written background file in one pass: 101 files reviewed, 97 with fix-level issues, all rewritten and re-accepted (`critique/stage8-*.yaml`). The three Haiku price lists were redone against the list-price table instead. Sol-written background files were not critiqued, and junk files were not reviewed.

Decisions and deviations from the spec are logged in `docs/decisions.md`.

## Public data and attribution

Assay value models were trained on benchmark sets from the **Therapeutics Data Commons** (Huang et al., *Therapeutics Data Commons: Machine Learning Datasets and Tasks for Drug Discovery and Development*, NeurIPS Datasets and Benchmarks 2021), downloaded from TDC's Harvard Dataverse: hERG and hERG (Karim et al.), CYP1A2/2C9/2C19/2D6/3A4 inhibition (Veith et al.), microsomal and hepatocyte clearance (AstraZeneca, via ChEMBL), Caco-2 permeability (Wang et al.), aqueous solubility (AqSolDB), plasma protein binding (AstraZeneca, via ChEMBL) and lipophilicity (AstraZeneca, via ChEMBL). ChEMBL-derived data is licensed CC BY-SA 3.0. No public record (structure or measurement) is reproduced in the archive; the models are only applied to invented compounds.

## Regenerating

```bash
brew install --cask libreoffice && brew install tesseract poppler
uv sync
scripts/fetch_public_data.sh        # public TDC files -> data/public/
uv run mockgen world validate
uv run mockgen numbers              # deterministic, seed 1369
uv run mockgen render --all         # content JSON -> output/ (no model calls)
uv run mockgen validate --all
uv run mockgen golden
uv run mockgen export
```

Re-rendering from the committed `content/` reproduces the archive without any model calls. Git does not keep file modification times, so run `uv run mockgen export` after cloning to restore each file's archive date (it also rewrites `output/MANIFEST.tsv`). Writing new content uses `mockgen next` (which prints the model target for each batch), `mockgen pack <id>`, `mockgen submit <id> <json>` and `mockgen commit <id>`; the writer briefs are in `briefs/`.

## Known limitations

- Some reports are shorter than their manifest target length.
- Where the world has no measured values for a file (some price lines, individual-animal records, lot masses), documents describe outcomes qualitatively or leave `[TBC]`.
- A few world quirks remain, for example two people share the title Group Commercial Director.
- Name screening used web search, not company registries.
