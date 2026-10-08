# portco-mock-dataset

A fictional document archive for demoing AI Brain on a buy-and-build portfolio company (DEV-1369, DEV-1370). Everything in it is invented: the firms, people, clients, compounds, projects and results.

- **Ready to ingest:** `tarnovell_archive.zip` (306 files) first, then `tarnovell_firm_G_heldback.zip` (34 files, firm G) for the acquisition step. Unzipped sources: `output/archive/` and `output/heldback_firm_G/`.
- **Answer key:** `output/golden_set.json`. Don't ingest it.
- **How it was made and how to regenerate it:** [`docs/datasheet.md`](docs/datasheet.md).

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

File dates are part of the realism and `zip` keeps them. After cloning, run `uv run mockgen export` once to restore the dates (git doesn't store them). Then:

```bash
cd output/archive && zip -r -X ~/Desktop/tarnovell_archive.zip . -x '.DS_Store' '*/.DS_Store'
cd ../heldback_firm_G && zip -r -X ~/Desktop/tarnovell_firm_G_heldback.zip . -x '.DS_Store' '*/.DS_Store'
```

All names were screened so they don't clash with real companies or people.
