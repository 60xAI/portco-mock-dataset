# Stage 3 brief: build the fictional world core (staged)

You are building the structured "world" behind a fictional mock document archive. The archive belongs to a fictional drug-discovery and analytical services group built from acquisitions over ~30 years. Later, other agents write ~340 documents (decks, workbooks, reports, proposals) from this world, so every fact here must be internally consistent. You write YAML only; no documents.

Repo: `/Users/kertlaansalu/projects/portco-mock-dataset` (git, branch `main`, remote `origin`).
Read first:
- `/Users/kertlaansalu/projects/portco-mock-dataset/docs/spec-DEV-1370.md`: sections "The fictional world", "Planted answers (golden set)", "Style guides".
- `/Users/kertlaansalu/projects/portco-mock-dataset/names/names.yaml`: screened names. Use these names exactly. Don't invent new company or key-person names. Exception: background staff come from a script (below), and you may give the 2-4 extra named staff per firm realistic names only if you run each through the blocklist check in "Rules".
- `/Users/kertlaansalu/projects/portco-mock-dataset/src/mockgen/world.py`: the exact schema (pydantic models) and every validation rule. Your YAML must satisfy it.
- `/Users/kertlaansalu/projects/portco-mock-dataset/world/assays.yaml`: the canonical assay catalogue (fixed ids). You fill in per-firm `variants`.

World "today" is 2026-10-08. Dates are ISO `YYYY-MM-DD` in YAML.

## Stages (in order; validate after each; don't start a stage until the previous one passes)

Run validation from the repo root: `uv run mockgen world validate --stage <stage>`. It prints numbered errors. Fix them all before moving on. Warnings are OK.

### 1. group → `world/group.yaml`

Top-level key `group:` with fields of `Group` in world.py. Timeline: firm A (founding company, medicinal chemistry, UK, founded ~1994) becomes the platform. `group.formed` = the date A started acting as the group platform (equal to firm A's `joined_group`). The group brand and template may come later (e.g. a rebrand after PE investment); put the story in `history`. `brand_line_pattern` like `"{firm}, a Tarnovell company"`. `integration` = the current integration programme (started ~2024-2025, lead = the `integration_director` person id you will create in stage 3, e.g. `ST09`; 5-8 workstreams such as price harmonisation (in progress, half-finished), brand migration, LIMS consolidation, cross-sell, HR/payroll, IT/SharePoint migration). `share_root` is the head-office share name, e.g. `Tarnovell_Group`.

### 2. firms → `world/firms.yaml` and per-firm assay variants in `world/assays.yaml`

Top-level key `firms:`, a list of 7 `Firm` records A-G, using the names and locations from names.yaml. Required shape:
- A: `role: founder`, founded ~1994, `joined_group` = group.formed.
- B-F: `role: acquired`, acquisitions spread from ~1996 to 2024 (B early, F late is natural but not required). Each firm founded before its acquisition; `file_era_start` gives ~30 years of files for A, ~25 B, ~20 C, ~15 D, ~15 E, ~10 F (approximate), ~18 G.
- G: toxicology, `role: held_back`, `joined_group: 2026-10-01` (acquired now; its archive is not integrated yet). G has only `legacy` templates.
- Each firm is a distinct company: its own `share_root` (e.g. `\\ashfs01\Projects`-style or `B-Drive`, keep it a single folder-name-safe string like `AshcombeData`), `naming_style` (folder and filename habits with examples), `id_formats` (project ID and LIMS ID formats with Python regexes; they must differ between firms and the LIMS format must differ from the filename/project format), `date_convention` UK or US (at least 2 US firms), `date_formats`, `units_notes`, `username_style` (one of `{f}{last}`, `{last}{f}`, `{first}.{last}`, `{f}.{last}`, `{first}{l}`), `email_domain` (fictional, e.g. `ashcombe-discovery.co.uk`), `voice` (2-4 sentences: how their documents sound), `terminology` (8-15 house terms, e.g. `"study": "programme"`), `typical_lengths` (deck/report/proposal lengths), `templates` (legacy → transition after acquisition → group; colours as hex, fonts that existed in the era, `footer_text`, `brand_line` e.g. `"Brindle Biosciences"` then `"Brindle Biosciences, a Tarnovell company"`), `transition_rules` (what changed when and how fast), `history` (3-6 bullet strings: founding, key events, acquisition, leavers).
- Templates: ordered, non-overlapping, the last one open-ended (`to: null`); transition/group templates start on or after `joined_group`.
- In `world/assays.yaml`, fill `variants` for each assay with the house names each firm uses, keyed by firm letter, e.g. `herg: variants: {B: ["hERG QPatch", "hERG patch clamp"], C: ["IKr inhibition"], G: ["hERG (IKr) safety pharmacology"]}`. Only firms that offer the service. Need ≥3 distinct hERG names across firms and ≥2 distinct CYP-panel names (e.g. "CYP3A4 inhibition" / "3A4 DDI screen"). Don't change ids, names, endpoints or units.

### 3. people → `world/people.yaml`

Top-level key `people:`. Write only named staff (≈35-45): the 10 key staff from names.yaml (ids `ST01`-`ST10`, `key: true`, `role_hint` as given, variants exactly 3 forms: `"Dr F. Surname"` (or `"F. Surname"` without a doctorate), `"Firstname Surname"`, username) plus 2-4 extra named staff per firm and head office (ids `NS01`…, `key: false`) whom you need as project leads, study directors, BD people, QA managers, founders and leavers. Each person has `roles` (ordered spells with `unit` = firm letter or `HO`, `from`, `to`), `joined`, `left` (null if still employed), `home_firm`, `service_line` (a service line id or `admin`), `username` in their firm's `username_style`.
Story constraints:
- `leaver_old_laptop`: senior in vitro biologist at B, left (between 2015 and 2023); their old laptop folder will appear in the archive.
- `q2_lead_B_early`: B study director employed at B through the early 2010s; `q2_lead_B_recent`: at B in the early 2020s (still employed). `q2_lead_C_early`: C DMPK lead mid-2010s, has left. `q2_lead_C_recent`: at C in the 2020s.
- `bioinf_lead_D`: D head of bioinformatics, employed 2010s-now. `founder_A`: founded A, later group chair (an HO role). `group_ceo`: HO. `integration_director`: HO, joined ~2024. `tox_lead_G`: at G for 10+ years.
- Employment windows must cover every project they lead (stage 5).
Then run the deterministic filler to add background staff: `uv run mockgen world fill-staff --total 200`. It appends `BGnnn` people from Faker. Don't hand-edit BG people. Re-run the filler if you change named staff (it regenerates BG entries). Then validate `--stage people`.

### 4. clients → `world/clients.yaml`

Top-level key `clients:`, 70 `Client` records from names.yaml (ids `CL001`… as in names.yaml). `variants` lists which firm used which name and when (`{name, firm, from, to}`); a client used by a firm under its canonical name still needs a variant entry for that firm with the canonical name. Background clients: 1-3 firms each, plausible for their segment.
The q3 target (cross-sell client) has exactly 4 distinct names across firms A, C, E and G (e.g. A used "Corvenlea Pharma" 2001-2009, C used "Corvenlea Ltd" 2012-2018, E used "Corvenlea Pharmaceuticals plc" 2019-now, G used "Corvenlea (US)" only), never D or F, and the G name is used nowhere else. `notes` explains the corporate story (rename, plc listing, US subsidiary). The lookalike (`role: q3_lookalike`, `lookalike_of: <target id>`) is a different company, used at one or two firms (it may buy from D or F; that's part of the trap).

### 5. projects → `world/projects.yaml`

Top-level key `projects:`, about 130 `Project` records (ids `PRJ0001`…), spread roughly A 18, B 26, C 24, D 14, E 20, F 12, G 16, over each firm's era (more in recent years, a few early). Status mix ≈ 65% completed, 15% in_progress, 12% lost/unanswered, 8% on_hold/cancelled. Prices in the firm's currency, realistic for a CRO (e.g. hERG+CYP on 40 compounds ≈ £14k-£30k; DMPK packages £8k-£60k; stability studies £25k-£120k; GLP tox £80k-£400k; bioinformatics engagements £15k-£150k), drifting with inflation by year. `turnaround_days` = calendar days start→completion for completed projects (must equal the date difference), null otherwise. `client_variant` must be one of the client's variant names valid at that firm on the quote date. Lead and team must be employed at that firm on the quote, start and completion dates. `series_id` names a compound series you define in stage 6 (ids `SER01`…); every project that runs compound assays (herg, cyp_*, kinase_*, mic_stab, hep_stab, ppb, caco2, solubility, cytotox, ames, micronucleus) needs a series and `n_compounds`.
Planted projects. Each tag goes on exactly one project (validator enforces the rules):
- `q2_correct_B1`, `q2_correct_B2` (firm B), `q2_correct_C1`, `q2_correct_C2` (firm C): completed, assays include `herg` and `cyp_inhib` (optionally `cyp_ic50`), 36-44 compounds from a kinase series, turnaround ≤21 days, all four in different years spread over ~2011-2024, leads = the four q2 lead people.
- `q2_distractor_herg_only`: herg without any CYP assay (ideally a kinase series, ~40 compounds; B or C).
- `q2_distractor_cyp_other_chemotype`: cyp_inhib on a non-kinase series (e.g. GPCR antagonists).
- `q2_distractor_right_client_wrong_assay`: same client as one q2_correct project, but different assays (e.g. mic_stab + ppb), no herg/cyp.
- `q3_target_A`, `q3_target_C`, `q3_target_E`: projects for the q3 target client at A, C and E under the variant valid then. Give the q3 client 1-2 more projects at those firms too if natural, never at D or F.
- `q3_lookalike`: a project for the lookalike client.
- `q4_G1`, `q4_G2`: firm G, completed, herg + cyp_inhib on 36-44 kinase compounds, ≤21 days (an in vitro safety pharmacology package); at least one for the q3 target client under its G-only 4th variant.
- `q5_structbio_D`: firm D, crystallography-based docking / structure-based design (structural biology mention). `q5_structbio_A`: firm A, a structural biology collaboration (X-ray co-crystal structures used to guide chemistry). Nothing anywhere mentions cryo-EM.
Validate `--stage projects`.

### 6. compounds → `world/compounds.yaml`

Top-level key `series:`, one `Series` per chemical series used by projects (≈15-25 series). Each has an invented `core_smiles` with mapped attachment points (`[*:1]`, `[*:2]`), `r_groups` keyed `"1"`, `"2"` with 6-12 fragment SMILES each, each fragment carrying exactly one matching `[*:n]` (e.g. `"[*:1]c1ccc(F)cc1"`, `"[*:2]N1CCOCC1"`). The script enumerates the products with RDKit; each series must enumerate ≥ the largest `n_compounds` of any project using it (≥12 always; ~40+ for q2/q4 series). `is_kinase: true` for kinase chemotypes (hinge binders: aminopyrimidines, pyrazolopyrimidines, quinazolines, pyrrolopyridines…), false for others (GPCR ligands, protease inhibitors, ion-channel blockers, nuclear receptor ligands…). Cores must be invented drug-like scaffolds, not a known drug. `compound_prefix` is the client's compound-ID prefix (e.g. `CVL`), `client_id` the owning client. Validate `--stage compounds`, then run the full check: `uv run mockgen world validate`.

## Rules

- Never use these, anywhere, even partially: Halden, Northgate, NGP, Thompson, or any real CRO, CDMO, pharma or vendor name (see `/Users/kertlaansalu/projects/portco-mock-dataset/config/blocklist.yaml`). Check any extra person name with `uv run python -c "from mockgen.names import Blocklist; print(Blocklist.load().check_name('Firstname Surname', person=True))"` (None = ok).
- No cryo-EM anywhere. Structural biology only in the two q5 projects (and maybe a firm history line).
- Don't edit anything under `src/`, `docs/`, `config/` or `names/`. If the validator seems wrong, work around it, and note the problem in your final reply.
- Generate and validate only: don't write tests, don't review code, don't invoke any skills.

## Finish

1. `uv run mockgen world validate` passes with 0 errors.
2. Commit and push: `git add world/ && git commit -m "Stage 3: world core" && git push` (if rejected: `git pull --rebase`, then push).
3. Reply briefly: the firm timeline (letter, name, founded, joined_group, location), counts (people, clients, projects by firm and status, series), the planted projects (tag → project id, firm, client variant, year, lead), and any validator issues you worked around.
