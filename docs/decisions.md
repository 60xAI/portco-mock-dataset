# Decisions log

One line per decision taken during the build where the spec was silent or ambiguous. The spec is `docs/spec-DEV-1370.md`.

- 2026-10-08 · Build brief overrides the spec: no test suite and no code review rounds; the toolkit is throwaway internal tooling that only has to run. `submit` still runs the spec's gate checks (schema, blocklisted/unregistered names, numbers vs world, planted facts, employment-window dates, 350 cap).
- 2026-10-08 · Build brief overrides "not pushed": repo pushed to a private GitHub repo under the 60xAI org, direct to main.
- 2026-10-08 · Python pinned to 3.13 (RDKit/unstructured wheels); uv venv in `.venv` inside the repo.
- 2026-10-08 · World data stored as YAML under `world/`, one file per stage; manifest as YAML under `manifest/` (one file per firm + head office), merged by `mockgen manifest validate`.
- 2026-10-08 · Claims and generation state in SQLite (`state/claims.db`) guarded by a file lock; claim timeout 45 minutes.
- 2026-10-08 · World core needed a second Sol round: round 1 was template-generated (110/130 projects quoted on 15 Jan, "work package NN" titles, identical outcomes). Realism checks were added to `mockgen world validate` (date spread, title stems, repeated outcomes, ID sequences, assay house names, filename habits, drug-like enumerated compounds) and round 2 fixed the data.
- 2026-10-08 · Assay numbers use RandomForest models trained on TDC ADMET sets (hERG Karim, CYP Veith ×5, AZ microsomal/hepatocyte clearance, Caco-2 Wang, AqSolDB, AZ PPB, AZ logD), downloaded to `data/public/` (gitignored). CYP classifier outputs are rank-calibrated to per-isoform hit rates (1A2 15%, 2C9 20%, 2C19 20%, 2D6 12%, 3A4 30% at >50% inhibition @10 µM) because raw probabilities gave ~100% 1A2 hits.
- 2026-10-08 · Content numbers are never typed by writers: text uses `{{PRJnnnn:key}}` placeholders and tables use `table_ref`/`data_refs`, resolved by the renderer from `numbers/`. "Numbers match the world" is enforced by construction plus a check on any cell that carries a `ref`, compound-count statements and planted prices.
- 2026-10-08 · Planted-answer files are specified by `mockgen manifest seed-planted` (43 entries, ids P01-P43, `manifest/planted.yaml`) with required facts checked on submit; firm manifest agents only choose their path and filename.
- 2026-10-08 · The CRM client-list CSV is an unmerged export (one row per legacy name); variant bridging lives in the head-office identity workbook and cross-sell deck, matching the spec's "bridging documents".
- 2026-10-08 · The q4 4th variant ("Corvenlea (US)") is rejected by `submit` anywhere outside firm G; the q3 client is rejected in D and F files.
- 2026-10-08 · Deck page/slide numbering for the golden set comes from `unstructured` partitioning; PDFs use strategy "fast".
- 2026-10-08 · Filesystem birth time can't be set on macOS without Xcode tools; only mtime/atime are set to the file's modified date. Document properties carry created/modified/author/last-saved-by/company.
- 2026-10-08 · Pilot pack (10 files, orchestrator-written): B-008 readout pptx + B-046 its PDF export (swapped in for C-007, whose project has no compound numbers), A-001 1997 .ppt, B-034 leaver .xls, C-037 2006 .doc, E-037 scan, E-046 service catalogue PDF, HO-006 price harmonisation xlsx, G-026 SOP docx, F-019 client report PDF. CSV format is covered by the three planted script CSVs.
- 2026-10-08 · Before the Tarnovell brand launched (2020-01-01) the group is called 'the Vellacombe group' (A was the platform). `submit` rejects 'Tarnovell' in files last saved before 2020.
- Stage 7: a rejected file stays claimed by its batch, and pack/submit refresh the batch's 45-minute claim, so parallel children never get handed a file another child is still working on.
- Stability tables: one t=0 analysis serves every storage condition, and in-progress stability studies are cut only by months elapsed (not by the generic interim row cut); accepted E files re-rendered.
- cyp.most_flagged names every isoform tied for the top count (e.g. 'CYP2C19, CYP2D6 and CYP3A4'); added cyp.most_flagged_n.
- hERG table title says manual patch clamp when the project title does (PRJ0033, 2003); interim notes count planned rows, not compounds (fixes '35 of 32').
- List prices: src/mockgen/prices.py gives deterministic list prices per firm/service/year (2024 anchors from HO-006, +3.5%/yr, USD for US firms); packs for price lists, catalogues and capability decks show them.
- List prices: src/mockgen/prices.py gives deterministic list prices per firm/service/year (2024 anchors from HO-006, +3.5%/yr, USD for US firms); packs for price lists, catalogues and capability decks show them.
- Stage 7 tail: leftover singletons are batched by firm where possible, otherwise as mixed-firm batches of the same tier (dev1369-content-mixed-NN).
- Stability results stop at completion, else at the last (interim) report date for open, held or cancelled studies.
