# Stage 3, round 2: make the world core realistic

The original brief is `/Users/kertlaansalu/projects/portco-mock-dataset/briefs/stage3-world.md`; read it again first. All of its rules still apply. Round 1 produced `world/*.yaml` (committed as `87ab58b`). It passed the validator, but it reads as machine-generated. Later agents write ~340 documents from this world, and a scientist or PE operating partner will look at the dates, IDs and titles in a LIMS export and in filenames. Repetitive placeholders would give the game away.

The validator now has realism checks. `cd /Users/kertlaansalu/projects/portco-mock-dataset && uv run mockgen world validate` currently fails with 68 errors. Make it pass with 0 errors by fixing the data, not by gaming the checks.

## Findings from review of round 1 (fix all)

1. **Project dates.** 110 of 130 projects are quoted on 15 January with a start on 29 January. Spread quote dates across the whole year, with realistic gaps: quote to start 1-8 weeks, start to completion matching the work (a 40-compound hERG/CYP screen 2-3 weeks; DMPK packages 3-8 weeks; stability studies 6-36 months; GLP tox 3-9 months; synthesis 2-6 months). Avoid weekends for quote, start and completion dates. Keep `turnaround_days` equal to completion - start.
2. **Project IDs.** Every firm's IDs run 0001, 0002… across the whole world. A real CRO's sequence numbers reflect its annual volume (e.g. `BW11_0147`, `MV-2015-083`); the archive only holds a sample of its projects. Make sequence numbers plausible per firm and year, increasing with date within a year. LIMS IDs likewise.
3. **Titles.** 115 titles are "<generic stem> — work package NN". Write a specific, varied title for every project, the way a project manager would: client programme or target, assay, compound count or batch, e.g. "AP-02 hinge-binder follow-up: hERG + 5-CYP panel (42 cpds)", "Lot 3 tablets 12-month ICH stability", "Exploratory 7-day rat DRF, OT-1192".
4. **Outcomes.** 85 completed projects share "Deliverables accepted; controls met protocol acceptance criteria." Write a specific one-sentence outcome per project: what was found, what the client did next, or why it was lost or paused (lost on price, client went in-house, funding round delayed, compound dropped for tox…). For planted q2/q4 projects, the outcome mentions the headline result in words (no numbers; numbers come from a script).
5. **Assay house names.** Variants such as "Brindlewythe Primary kinase IC50" and "Merrivoss Liver microsomal stability" are the canonical name with a firm prefix. Replace them with what staff at that firm actually call the assay (e.g. hERG: "hERG QPatch", "hERG patch clamp", "IKr inhibition", "hERG (IKr) safety pharmacology"; CYP: "CYP3A4 inhibition", "3A4 DDI screen", "5-isoform CYP panel"; microsomal stability: "HLM/RLM stability", "met stab", "microsomal CLint"; PPB: "RED PPB", "fu,p by equilibrium dialysis"). Different firms should differ. Also fix the `bioinf` entry if needed: its `name` must stay exactly "Bioinformatics analysis (target ID, omics, NGS)"; don't change ids, names, endpoints or units of any assay.
6. **Firm filename habits.** Every firm's `filename_examples` follow `<ID>_Report_v2.doc` and `<letter>_<date>_Readout_FINAL.pptx`. Give each firm ≥4 examples in its own style (case, separators, date formats, client codes, version habits; US firms might use `MMDDYY`; a 1990s chemistry firm might use 8.3-style names like `CVL0412.DOC`). Make the folder examples distinct too. `typical_lengths` also step up mechanically by +1 per firm; make them fit each firm's work.
7. **Named staff.** Every firm's extra named staff are the same four roles (Site Scientific Director, Study Scientist, QA Manager, BD Manager). Vary the roles to fit each firm (e.g. electrophysiology team lead, mass-spec manager, stability coordinator, formulation lead, GLP archivist, head of BD North America). Keep IDs `ST01`-`ST10` and their role hints unchanged. You may rename `NS` people only if they're not referenced by projects, or update the references.
8. **Compound series.** Cores are tiny (2-aminopyrimidine with two R groups), so enumerated compounds have median MW ~250. Real lead-optimisation series are larger: use cores of 10-18 heavy atoms (bicyclic heteroaromatics, biaryls, amide-linked cores) and fragments such as substituted anilines, solubilising amines (morpholine, N-methylpiperazine, 4-aminopiperidine), heteroaryls and small amides. The validator wants median MW 300-560 and ≥3 rings per compound. Keep series ids, owning clients and prefixes; keep kinase / non-kinase assignments.

## Keep unchanged

- All names (group, firms, clients, staff `ST01`-`ST10`) and the client variant periods, including Corvenlea's 4 variants.
- Project ids `PRJ0001`-`PRJ0130`, their firm, client, status, planted tags, assays, series and lead. You may adjust `n_compounds` within the planted rules, and team members.
- Firm founding, acquisition dates, templates and `share_root`.

## How to work

- Edit `world/*.yaml` directly (a helper script is fine, but the output must read as hand-curated). If you change named staff, re-run `uv run mockgen world fill-staff --total 200`.
- Validate: `uv run mockgen world validate` must report 0 errors.
- Don't edit `src/`, `docs/`, `config/` or `names/`. Don't write tests, don't review code, don't invoke any skills.
- Commit and push: `git add world/ && git commit -m "Stage 3: world core realism pass" && git push` (if rejected, `git pull --rebase`, then push).

## Reply

Briefly: 0-error confirmation, 5 example project lines (id, firm id, LIMS id, title, dates, outcome), the hERG and CYP house names per firm, and anything you couldn't fix.
