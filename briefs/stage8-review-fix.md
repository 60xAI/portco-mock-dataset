# Stage 8 brief: review and fix accepted archive files in one pass

You review and then fix the CONTENT of files in a fictional mock document archive (Tarnovell Bioscience Group, built from acquired firms over 30 years). The files were written by a faster model and are often wrong in the same ways: prose that contradicts the tables (QC rules, flags, repeats, counts, trends), invented compound ID ranges, lots or measurements, missing brand lines in group-era files, dates or events that don't fit the file date, and claims the data doesn't support. Repo: `/Users/kertlaansalu/projects/portco-mock-dataset`; run every command from the repo root.

For each file id in the task message:
1. `uv run mockgen pack <file-id>`: the world facts, numbers (`{{PRJnnnn:key}}` values and `table_ref` tables with their rows and notes), people, era and rules the file must follow. Read `briefs/stage7-content.md` once for the writing rules and `briefs/critique.md` once for the review criteria.
2. Read `content/<file-id>.json`. Resolve placeholders against the pack mentally and check: scientific plausibility; firm voice and era; consistency with the world (client name, people and roles at the time, dates, prices, counts); prose agreeing with the tables; nothing invented that the pack doesn't support; no text about "the pack" or "supplied data".
3. If you find `fix`-level problems (a scientist or PE operating partner would notice, or a fact contradicts the world or the tables), edit `content/<file-id>.json` to fix them. Keep the file's finish state and texture flags (draft, half-filled, comments, typos, mixed units). Never type result values by hand and never invent IDs, lots or measurements; reference source records qualitatively instead. Polish `minor` issues only if cheap.
4. If you edited it: `uv run mockgen submit <file-id> content/<file-id>.json` (fix every numbered reason if REJECTED; up to 3 attempts), then `uv run mockgen commit <file-id> -m "Stage 8 review fixes: <file-id>"`. Never use `git add -A`, `git stash`, `git reset`, `git checkout` or `git pull`: other agents' work is in this tree.

Record what you found in `critique/<batch-name>.yaml` (batch name in the task message), one entry per file:

```yaml
- file_id: A-013
  verdict: ok | minor | fix
  fixed: true | false
  issues:
    - severity: fix | minor
      area: science | voice | consistency | realism
      problem: "..."
      change_made: "... or 'not changed: <reason>'"
```

Commit only that file: `git add critique/<batch-name>.yaml && git commit -m "Critique <batch-name>" -- critique/<batch-name>.yaml && git push` (if the push is rejected, run `uv run mockgen commit` for any file id of yours, which syncs safely, then `git push`).

Don't edit anything outside `content/` and `critique/`. Don't write tests, don't review code, don't invoke any skills.

Reply: counts of ok/minor/fix, how many files you changed, and the three most common problems.
