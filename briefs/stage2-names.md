# Stage 2 brief: generate and screen fictional names

You are generating and web-screening the names for a fictional mock document archive. The archive belongs to a fictional drug-discovery and analytical services group built from acquisitions. Every name must be fictional and must not collide with a real company or a real person in pharma, biotech or contract research.

Repo: `/Users/kertlaansalu/projects/portco-mock-dataset` (git, remote `origin` = private GitHub repo, branch `main`).
Background reading (optional): `/Users/kertlaansalu/projects/portco-mock-dataset/docs/spec-DEV-1370.md`, sections "Names" and "Planted answers".

## What to produce

Two files, both YAML:

1. `/Users/kertlaansalu/projects/portco-mock-dataset/names/names.yaml`
2. `/Users/kertlaansalu/projects/portco-mock-dataset/names/screening.yaml`

### names.yaml

```yaml
group:
  name: "Tarnovell Bioscience Group"      # full brand name
  short_name: "Tarnovell"
  legal_name: "Tarnovell Bioscience Group Ltd"
  screening_id: S001
firms:            # exactly 7, letters A-G
  - letter: A
    service_focus: "Medicinal chemistry"
    legacy_name: "..."        # full legal-style name, e.g. "Ashcombe Discovery Ltd"
    short_name: "..."         # how staff say it, e.g. "Ashcombe"
    naming_basis: "founder surname" | "place name" | "invented word" | ...
    location: {city: "...", country: "UK" | "US" | ...}
    screening_id: S00x
clients:          # 15 key clients + 55 background clients = 70
  - id: CL001
    canonical_name: "..."
    variants: ["...", "..."]   # see rules below; [] for most clients
    role: q3_target | q3_lookalike | key | background
    segment: big_pharma | mid_pharma | biotech | virtual_biotech | academic | agrochem | animal_health | generics
    location: {city: "...", country: "..."}
    screening_id: S0xx
staff:            # 10 key named staff
  - id: ST01
    full_name: "Firstname Surname"
    title: "Dr" | null
    variants: ["Dr F. Surname", "Firstname Surname", "fsurname"]   # 3 forms: titled initial, full, username
    role_hint: "..."            # from the list below
    nationality: "..."
    screening_id: S0xx
rejected:         # every candidate you screened and dropped, with the reason
  - name: "..."
    kind: group | firm | client | staff
    reason: "..."
```

### screening.yaml

A list, one entry per screened name (kept and rejected):

```yaml
- id: S001
  name: "Tarnovell Bioscience Group"
  kind: group | firm | client_key | client_background | staff
  depth: full | exact          # full for group, firms, key clients, staff; exact for background clients
  checks:
    - source: "UK Companies House"      # also: OpenCorporates, SEC EDGAR full-text/company search, LinkedIn, general web search, USPTO/UKIPO trademark search where relevant
      query: "Tarnovell"
      result: "no match"                # or a short description of what matched
  verdict: clear | clear_noncompeting_use | rejected
  notes: "..."
```

## The names needed

- **Group (1).** Already screened as safe in an earlier pass and preferred: "Tarnovell Bioscience Group". Re-screen it (full depth) and keep it unless you find a real life-sciences collision.
- **Firms (7)**, each a legacy business acquired into the group. Use real naming patterns without copying or parodying any specific real company: founder surnames ("Ashby & Moreton"), place names, "X Discovery", "X Biosciences", "X Analytical", "X Laboratories". Mix UK and US firms (at least 2 US). Focus areas:
  - A: medicinal chemistry, the founding company (UK, founded ~1994)
  - B: in vitro biology and screening (hERG, CYP, kinase panels)
  - C: DMPK and bioanalysis
  - D: bioinformatics and computational chemistry
  - E: analytical chemistry and stability testing
  - F: formulation and early CMC
  - G: toxicology (in vitro and in vivo, GLP), the most recent acquisition
- **Key clients (15):**
  - 1 `q3_target`: a pharma client known under **4 name variants** over time (canonical plus 3 variants; e.g. "X Pharma", "X Ltd", "X Pharmaceuticals plc", "X (US)"). Preferred, already pre-screened: Corvenlea → "Corvenlea Pharma", "Corvenlea Ltd", "Corvenlea Pharmaceuticals plc", "Corvenlea (US)". Re-screen at full depth.
  - 1 `q3_lookalike`: a different client whose name is confusingly similar to the q3 target (shares a prefix or sound), e.g. a "Corven..." biotech. Must also be clear.
  - 13 `key`: a mix of mid-size pharma, biotechs and one or two academic/charity drug-discovery units. Pre-screened candidates you may use: Avernelwick, Selverant, Tervemere, Elvarmere.
- **Background clients (55)**, `role: background`, exact-name search only (one web search per name for the exact string plus "pharma"/"therapeutics"; reject on any real life-sciences hit). Realistic small-biotech and pharma naming, varied, international, no two too similar except the q3 pair.
- **Key staff (10)**, realistic mix of nationalities. `role_hint` values, one each:
  1. `leaver_old_laptop`: a senior in vitro biologist at firm B who has left; their old laptop folder is in the archive (this replaces "Jim Thompson"; must NOT be Thompson or any Halden/Northgate name)
  2. `q2_lead_B_early`: firm B study director, early 2010s
  3. `q2_lead_B_recent`: firm B scientist, early 2020s
  4. `q2_lead_C_early`: firm C DMPK lead, mid 2010s, since left
  5. `q2_lead_C_recent`: firm C DMPK scientist, 2020s
  6. `bioinf_lead_D`: head of bioinformatics at firm D, author of the capability deck
  7. `founder_A`: founder of firm A and later group chair
  8. `group_ceo`
  9. `integration_director`: runs the group integration programme
  10. `tox_lead_G`: lead toxicologist at firm G

## Hard rules

- Blocklisted, never use, not even as part of a name: Halden, Northgate, NGP, Jim Thompson (or any "Thompson"). Also never use or echo any real CRO, CDMO or pharma name. The list is in `/Users/kertlaansalu/projects/portco-mock-dataset/config/blocklist.yaml`.
- No parody look-alikes of real companies (no "Pfyzer", "Novaris", "AstroZeneca").
- A name is `rejected` if the exact name (or the distinctive word in it) belongs to a real company, product or brand in pharma, biotech, CRO/CDMO, lab services or healthcare investing, or if a key staff full name matches a real, findable person in pharma/biotech/CRO. Common-word uses in unrelated industries can be `clear_noncompeting_use` (say what you found).
- Record every check you actually ran (source, query, result). Do not record a check you did not run. If a source is unreachable, record that in `result`.

## How to work

- Use web search. Do it in parallel where you can.
- Write the two YAML files. Check they parse: `cd /Users/kertlaansalu/projects/portco-mock-dataset && uv run python -c "import yaml; yaml.safe_load(open('names/names.yaml')); yaml.safe_load(open('names/screening.yaml')); print('ok')"`.
- Then commit and push: `git add names/ && git commit -m "Stage 2: names and screening" && git push` (if the push is rejected, `git pull --rebase` and push again).
- Generate and screen; don't test, review or verify beyond the YAML parsing. Don't invoke any skills. Don't edit files outside `names/`.

## Final reply

Reply with: the group name, the 7 firm names, the q3 target with its 4 variants, the lookalike, the 10 staff with role hints, and how many candidates you rejected (and the main reasons). Keep it short.
