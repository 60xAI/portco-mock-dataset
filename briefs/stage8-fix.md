# Stage 8 brief: apply critique fixes to accepted archive files

You fix the CONTENT of files in a fictional mock document archive (Tarnovell Bioscience Group, built from acquired firms). A reviewer has critiqued them; you apply the fixes. Repo: `/Users/kertlaansalu/projects/portco-mock-dataset`; run every command from the repo root.

For each file id in the task message:
1. Read the critique entry for the file in the critique YAML named in the task message.
2. `uv run mockgen pack <file-id>` for the world facts, numbers (`{{PRJnnnn:key}}` placeholders, `table_ref` tables with their rows) and rules. Read `briefs/stage7-content.md` once for the writing rules; they all still apply.
3. Edit `content/<file-id>.json` to resolve every `fix` issue and the `minor` issues that are cheap. Keep the file's texture flags (draft, half-filled, mixed units, comments). Never type result values by hand and never invent compound IDs, lots or measurements; where detail is missing, reference the source record qualitatively. Never write about the pack or the data you were given.
4. `uv run mockgen submit <file-id> content/<file-id>.json`. If REJECTED, fix every numbered reason and resubmit (up to 3 attempts).
5. When ACCEPTED: `uv run mockgen commit <file-id> -m "Stage 8 fixes: <file-id>"`. Never use `git add -A`, `git stash`, `git reset` or `git checkout`: other agents' work is in this tree.

Don't edit anything outside `content/`. Don't write tests, don't review code, don't invoke any skills.

Reply: one line per file: `<file-id> FIXED` or `<file-id> NOT FIXED: <reason>`.
