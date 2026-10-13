# portco-mock-dataset

A fictional document archive for demoing AI Brain on a buy-and-build portfolio company (DEV-1369, DEV-1370). Everything in it is invented: the firms, people, clients, compounds, projects and results.

![Tarnovell before and after AI Brain: double-siloed systems, then every firm's connectors feeding one knowledge graph that all 200 staff query](docs/architecture/ai-brain-architecture.gif)

The animation's source is [`docs/architecture/ai-brain-architecture.html`](docs/architecture/ai-brain-architecture.html); regenerate the GIF with `uv run --script docs/architecture/render.py`.

- **Ready to ingest:** the eight zips in `tarnovell_archive/` first (306 files, one zip per top-level folder; select them all in one upload), then `tarnovell_firm_G_heldback.zip` (34 files, firm G) for the acquisition step. Every zip is under AI Brain's 30 MB upload limit; the archive as one zip (49 MB) is not. Unzipped sources: `output/archive/` and `output/heldback_firm_G/`.
- **Why firm G is held back:** buy-and-build groups keep acquiring, so the demo needs to show what happens the day a new company's archive lands. Firm G (Osterquill Toxicology) is the newest acquisition, closing on 1 October 2026. You ingest the main archive and ask a question, then ingest firm G and ask the same question again. New answers appear straight away: two more matching projects, and a client record ("Corvenlea (US)") that links to the group's existing Corvenlea history. That shows AI Brain makes a newly bought firm's knowledge usable from day one, without any integration work.
- **Answer key:** `output/golden_set.json`. Don't ingest it.
- **How it was made and how to regenerate it:** [`docs/datasheet.md`](docs/datasheet.md).
- **Next generation run:** start with the [generation workflow](#generating-and-reviewing-content) below. [`briefs/orchestration.md`](briefs/orchestration.md) has the full dispatch and recovery procedure.

## Generating and reviewing content

The generation safeguards added in [PR #2](https://github.com/60xAI/portco-mock-dataset/pull/2) help catch source contradictions, prevent overlapping Git operations, and check each writer tier before bulk work. Run commands from the repository root and read [`briefs/stage7-content.md`](briefs/stage7-content.md) before writing.

1. Run `uv run mockgen preflight` and resolve every source error. Keep the world, number tables, manifests, price rules and exemplars fixed while writers run.
2. Pilot each writer tier with its own configured target before bulk dispatch. The current policy requires 10 original submissions, at least 9 `ok` or `minor` verdicts, at most 1 `fix`, no source contradictions, and accepted resubmissions for every fix. Save original verdicts in `critique/pilot-<tier>.yaml` and the decision in `docs/generation-run.md`. The orchestrator approves this gate; `mockgen next` enforces routing. A failed tier's remaining work must move to the stronger tier through `writer_policy.promoted_tiers`.
3. Claim work, obtain each file's pack, write content using its exact names and tables, then submit with the fingerprint printed in that pack:

   ```sh
   uv run mockgen next --tier <tier> --batch 6 --who <writer>
   uv run mockgen pack <file-id>
   uv run mockgen submit <file-id> content/<file-id>.json --source <pack-fingerprint>
   uv run mockgen commit <file-id>
   ```

   Targets and limits live in [`config/models.yaml`](config/models.yaml). Scientific workbooks, reports, readouts, pricing and scientific copies use the stronger tier. Cheaper tiers handle bounded administrative content and junk. Near the end, `next` fills batches across firms and document families within a tier, while respecting explicit filters and source-copy dependencies.
4. Review all pilots, planted answers and cheap-tier files using [`briefs/critique.md`](briefs/critique.md). Apply fixes using [`briefs/stage8-review-fix.md`](briefs/stage8-review-fix.md), then resubmit them. Preserve the original pilot verdicts.

Accepted submissions record their source fingerprint in `content/<file-id>.source.json`. Finish with `uv run mockgen sources changed` and `uv run mockgen validate --all`. Changed sources require content review and resubmission against a current pack. Existing files without a receipt have untracked provenance and need the same review. Obtaining a new pack or re-rendering a file does not establish that its content matches the current sources.

During parallel work, use `mockgen commit <file-id>` for accepted content and `mockgen commit --path <exact-file> -m "<message>"` for review or source artifacts. Commit and sync share `state/git.lock`; avoid raw Git mutations during the run. Routine `uv run mockgen sync` allows only a fast-forward and refuses dirty trees or active claims. After a rejected push, stop dispatch, drain writers, commit their named files with `--no-push`, resolve or release claims, and clean the tree before `uv run mockgen sync --rebase`. Follow the [full recovery procedure](briefs/orchestration.md#git-coordination) before retrying the push.

## The fake world

**Tarnovell Bioscience Group** is a contract research group built over 30 years by buying small specialist labs. Each lab kept its own shared drive, file-naming habits and client names, so the group's knowledge is scattered across seven legacy archives. Finding it is the problem AI Brain solves in the demo.

### The group

```mermaid
flowchart TD
    HO["<b>Tarnovell Bioscience Group</b><br/>head office, UK<br/>brand used from 2020"]
    HO --> A["<b>A · Vellacombe Discovery</b><br/>Nottingham<br/>medicinal chemistry<br/>the founder, 1996"]
    HO --> B["<b>B · Brindlewythe Biosciences</b><br/>Cambridge<br/>in vitro biology: hERG, CYP<br/>joined 2001"]
    HO --> C["<b>C · Merrivoss Bioanalysis</b><br/>Madison, US<br/>DMPK and ADME<br/>joined 2008"]
    HO --> D["<b>D · Quenverell Computational</b><br/>Edinburgh<br/>bioinformatics and docking<br/>joined 2014"]
    HO --> E["<b>E · Westravelle Analytical</b><br/>York<br/>stability and analytical<br/>joined 2019"]
    HO --> F["<b>F · Durnesswick Laboratories</b><br/>Durham, US<br/>formulation<br/>joined 2024"]
    HO -.-> G["<b>G · Osterquill Toxicology</b><br/>Portland, US<br/>GLP toxicology<br/>joins 1 Oct 2026 · held back"]

    classDef ho fill:#1f3a5f,color:#fff,stroke:#1f3a5f
    classDef firm fill:#e8f0fa,stroke:#1f3a5f,color:#111
    classDef held fill:#fff4e0,stroke:#d08a00,color:#111,stroke-dasharray: 5 5
    class HO ho
    class A,B,C,D,E,F firm
    class G held
```

### How it grew

```mermaid
timeline
    title Acquisitions (the archive's "today" is 8 October 2026)
    1996 : Vellacombe Discovery founded (A)
    2001 : Brindlewythe joins (B)
    2008 : Merrivoss joins (C)
    2014 : Quenverell joins (D)
    2019 : Westravelle joins (E)
    2020 : The "Tarnovell" group brand launches
    2024 : Durnesswick joins (F)
    2026 : Osterquill deal closes on 1 October (G)
```

Before 2020 the group was simply "the Vellacombe group". Older files keep their original firm's look, names and date formats.

### What lives in it

```mermaid
flowchart LR
    P["200 people<br/>with job histories;<br/>some left"] --> PR
    CL["70 clients<br/>each firm spells<br/>them its own way"] --> PR
    S["20 compound series<br/>realistic molecules"] --> PR
    PR(["130 projects"]) --> D1["Proposal<br/>price and turnaround"]
    D1 --> D2["Results workbook<br/>assay numbers"]
    D2 --> D3["Report<br/>PDF or Word"]
    D3 --> D4["LIMS record<br/>different ID format"]
```

Around the projects sit capability decks, SOPs, trackers, price lists, memos, board packs, scanned signed reports, legacy .ppt/.xls/.doc files and junk (empty templates, "Copy of" files, leavers' old laptops). Assay numbers come from models trained on public ADMET data, so they look real to a scientist.

### One client, many names

The key client, **Corvenlea**, appears under a different name at each firm that worked with it. A lookalike company is the trap.

```mermaid
flowchart LR
    CV(("<b>Corvenlea</b><br/>one real client"))
    CV --- A1["Vellacombe, 2001-09<br/>'Corvenlea Pharma'"]
    CV --- C1["Merrivoss, 2012-18<br/>'Corvenlea Ltd'"]
    CV --- E1["Westravelle, 2019 on<br/>'Corvenlea Pharmaceuticals plc'"]
    CV -.- G1["Osterquill, held back<br/>'Corvenlea (US)'"]
    LK["'Corvenlith Therapeutics'<br/>at Quenverell and Durnesswick"]
    LK -. "different company:<br/>must NOT be merged" .- CV

    classDef client fill:#1f3a5f,color:#fff
    classDef trap fill:#fde2e2,stroke:#c0392b,color:#111
    class CV client
    class LK trap
```

The head office's client identity bridge and white-space matrix name these variants together, which is what lets AI Brain join them up.

## The demo

```mermaid
flowchart TD
    I1["Ingest output/archive<br/>firms A-F and head office"] --> Q1
    Q1["<b>Q1</b> Bioinformatics slide for a pitch<br/>→ best Quenverell deck and its PDF<br/>(typo copy, draft and 2012 version are distractors)"]
    I1 --> Q2["<b>Q2</b> hERG + CYP on ~40 kinase compounds, under 3 weeks<br/>→ 4 past projects at Brindlewythe and Merrivoss<br/>(3 near-miss distractors)"]
    I1 --> Q3["<b>Q3</b> Corvenlea's full history<br/>→ joins the name variants<br/>and shows services it never bought"]
    I1 --> Q5["<b>Q5</b> Have we done cryo-EM?<br/>→ No. Closest work: 2 structure-based projects"]
    Q2 --> I2["Ingest output/heldback_firm_G<br/>the acquisition closes"]
    I2 --> Q4["<b>Q4</b> Ask Q2 again<br/>→ 2 more matching projects appear from Osterquill"]

    classDef ingest fill:#fff4e0,stroke:#d08a00,color:#111
    class I1,I2 ingest
```

Each question has a planted answer. `output/golden_set.json` gives the expected files and the page or slide each answer is on.

### Packaging for ingestion

File dates are part of the realism and zips keep them. `uv run mockgen zips` restores the dates (git doesn't store them; it runs `mockgen export` first), then rebuilds `tarnovell_archive/*.zip` and `tarnovell_firm_G_heldback.zip`. It fails if any zip reaches the 30 MB upload limit.

All names were screened so they don't clash with real companies or people.
