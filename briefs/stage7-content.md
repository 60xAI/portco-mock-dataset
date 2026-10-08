# Stage 7 brief: write content for a batch of archive files

You are writing the content of 5-8 files in a fictional mock document archive: the shared drives of a drug-discovery and analytical services group (Tarnovell Bioscience Group) built from acquired firms over 30 years. Each file is a real Office or PDF document rendered from the JSON you write. Your files must read like real documents written by the named person, at that firm, in that year.

Repo: `/Users/kertlaansalu/projects/portco-mock-dataset`. Run every command from the repo root. Your batch id and file ids are in the task message.

## For each file id

1. `uv run mockgen pack <file-id>`. This prints everything you need: the file's manifest entry, the firm's style and era, the people and their roles at the time, the project record, the numbers you may use (as `{{PRJnnnn:key}}` placeholders and `table_ref` tables), the client name to use, related files, the content schema, an exemplar path and the prohibitions. Read it in full.
2. Write the content JSON to `content/<file-id>.json`, matching the schema for the file's family (deck, workbook, document or scan). Look at the exemplar named in the pack (`exemplars/<family>.json`) for shape. Accepted files such as `content/P12.json`, `content/P14.json` and `content/B-008.json` show the expected quality.
3. `uv run mockgen submit <file-id> content/<file-id>.json`. It validates, renders and reopens the file. If it is REJECTED, fix every numbered reason and resubmit. If a file still fails after 3 attempts, run `uv run mockgen release <file-id>` and report why in your reply.
4. When a file is ACCEPTED, commit it: `uv run mockgen commit <file-id>`. This commits and pushes your content JSON and rendered file safely, even with other agents working in the same checkout. Never use `git add -A`, `git stash`, `git reset` or `git checkout`: other agents' work is in this tree.

## Writing rules

- **Follow the pack.** Respect the finish state (final, draft, interim, superseded, abandoned, empty template) and every texture flag (comments, tracked changes, [TBC] placeholders, typos, mixed units, half-filled, leaver folder…). Hit the target length roughly.
- **Numbers come from the pack only.** Assay results, compound counts, prices and turnaround use `{{PRJnnnn:key}}` placeholders, `table_ref` blocks or sheet `data_refs`. Never type result values by hand. Protocol settings (concentrations tested, replicates, time points) are fine.
- **Names come from the pack only.** Use only the people, clients and firms the pack lists, with the client name the pack tells you to use. No real companies, CROs, vendors, instrument makers or people. Generic reference compounds and reagents are fine.
- **Stay in the era.** Use the firm's date format, units, terminology and brand line for that date. Before 2020 the group brand "Tarnovell" did not exist. Nobody appears before they joined, and no client name appears before it was in use.
- **Never mention cryo-EM.**
- **Never write about the pack or the data you were given** ("the supplied data", "the pack gives", "counts tie"). The document is written by the firm's staff. If the pack looks inconsistent, write around it and report it in your reply.
- **Prose must agree with the tables.** Before describing QC rules, flags, repeats, counts or recoveries, read the table's rows and notes in the pack and say what they say. Use real compound IDs from the tables; never invent ID ranges, extra lots or extra measurements. If a texture asks for detail the pack lacks (individual animals, lot masses), reference the source record qualitatively instead.
- **Brand line:** from the date the pack's era notes give for the group identity, put the firm's brand line (e.g. "<Firm>, a Tarnovell company") on title slides, report covers and workbook summary sheets.
- Write like the firm. Each firm has its own voice in the pack. Vary sentence structure and avoid boilerplate. Real documents are specific: sample counts, run dates, who checked what, what was decided.
- Readouts and capability decks use charts (`chart` with `ref`) and molecule grids (`image` `molecule_grid`) where the pack has data. Reports put the key table early.
- Output files must be plain JSON (no comments, no trailing commas, `true`/`false`/`null`).

## Don'ts

- Don't edit anything outside `content/`. Don't change `world/`, `manifest/`, `src/` or `config/`.
- Don't write tests, don't review or verify anything beyond `mockgen submit` succeeding, and don't invoke any skills.

## Reply

One line per file: `<file-id> ACCEPTED` or `<file-id> RELEASED: <reason>`, plus anything in the pack that looked inconsistent.
