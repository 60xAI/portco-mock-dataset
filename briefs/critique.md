# Critique brief: content review of generated archive files

You review the CONTENT of generated files in a fictional mock document archive (a drug-discovery and analytical services group built from acquisitions). You never review code. For each file in your batch, judge three things:

1. **Scientific plausibility**: study design, assay conditions, controls, units, reporting conventions (hERG patch clamp, CYP inhibition, microsomal/hepatocyte stability, PPB, Caco-2, ICH stability, GLP tox), and whether interpretations follow from the numbers shown.
2. **Firm voice and era**: does it read like this firm in this year (terminology, date format, brand line, template era, technology of the time)? Does it read like a human-made document rather than generated text?
3. **Consistency with the world**: client name used, people and roles at the time, project ids, dates, prices, compound counts, and the planted facts the file must carry.

Repo: `/Users/kertlaansalu/projects/portco-mock-dataset`. For each file id in the task message:
- Context: `uv run mockgen pack <file-id>` and `content/<file-id>.source.json`. The receipt records the writer's source fingerprint; the new pack shows current facts. A source change requires content re-review, including prose conclusions and trends.
- Content: `content/<file-id>.json` (numbers appear as `{{PRJnnnn:key}}` placeholders or `table_ref`s; the pack shows their values).
- Rendered file: the path printed by `uv run python -c "from mockgen import manifest as M; from mockgen.render import out_path; print(out_path(M.entries_by_id()['<file-id>']))"`. You may extract its text (e.g. `uv run python -c "from unstructured.partition.auto import partition; print('\n'.join(map(str, partition(filename='<path>'))))"`).

## Output

Write `critique/<batch-name>.yaml` (batch name in the task message):

```yaml
- file_id: P01
  verdict: ok | minor | fix
  issues:
    - severity: fix | minor
      area: science | voice | consistency | realism
      where: "slide 4" / "section 3.2" / "sheet hERG"
      problem: "..."
      suggested_change: "concrete replacement text or instruction"
```

`fix` means a scientist or a PE operating partner would notice, or a fact contradicts the world. `minor` means a polish suggestion. Be specific and brief. Don't rewrite files, don't run `mockgen submit`, don't write tests, don't invoke any skills. Commit only your critique file with `uv run mockgen commit --path critique/<batch-name>.yaml -m "Critique <batch-name>"`. On a push failure, report it to the orchestrator for the drain-and-sync procedure in `briefs/orchestration.md`. Never use raw Git during parallel work.

Reply with: counts of ok/minor/fix and the three most important problems.
