# Archive generation orchestration

Read `config/models.yaml` for targets, writer policy and batch limits. Run from the repository root.

## Freeze sources before dispatch

Run `uv run mockgen preflight`. Resolve every source error before starting writers. Keep `world/`, `numbers/`, manifests, price rules and exemplars fixed while writers run. Source edits require stopping writers, committing named artifacts with `mockgen commit --path <file> -m "<message>"`, rerunning preflight, and content re-review for every file reported by `uv run mockgen sources changed`. Re-rendering does not clear a source-change warning. Existing files without provenance are reported as untracked; never backfill their fingerprint without content review.

## Pilot each writer tier before bulk work

The format pilot and planted files written by the parent do not qualify. For every tier used in this run, dispatch `writer_policy.pilot.required_per_tier` files to that tier's own configured target. Default N is 10. Cover its allowed document types, firms, eras and texture flags. If fewer than N eligible files remain, use another tier; do not claim that an undersized pilot passed.

Have the configured critique target review every pilot file using `briefs/critique.md`. Save original verdicts and issues in `critique/pilot-<tier>.yaml`, with file IDs, writer tier, source fingerprint and content commit for each file. Assess the original submissions before fixes. Bulk dispatch requires at least 9 of 10 `ok` or `minor` verdicts, at most 1 `fix`, zero contradictions of source facts or tables, and successful resubmission of all fixes. Read thresholds from config if they change. Record the decision and counts in `docs/generation-run.md`; commit each exact artifact using `mockgen commit --path`. `mockgen next` enforces routing, but the orchestrator is responsible for this pilot gate.

If a tier fails, stop using it. Set `writer_policy.promoted_tiers` in config to include that tier, so `mockgen next` routes its remaining work to the stronger tier. If the stronger tier itself fails, halt bulk dispatch until its target or writing brief changes and a fresh pilot passes. Review and repair every file a failing tier already wrote. A changed target or writing brief needs a fresh pilot; fixes to a failed pilot do not count as a passing original pilot. Never relabel parent-written files as a tier's pilot.

## Dispatch after promotion decisions

Claim with `uv run mockgen next --tier <tier> --batch 6 --who t3`, then dispatch using the printed target and clientRequestId. Every task reads `briefs/stage7-content.md`, obtains its own packs and submits with the exact `--source` fingerprint printed in each pack. Administrative tiers may write only bounded administrative content without project/result interpretation. Scientific workbooks, study/report/readout content, pricing and scientific copies use the stronger tier regardless of their old manifest tier.

Keep at most the configured concurrency limit running. Near the tail, `next` fills across firms and families within a tier when the eligible pool is at most `tail_pool_max`. Explicit firm/type filters and source-copy dependencies still apply. No handwritten claims or scratch batching scripts.

Critique all planted answers, all pilots and every cheap-tier file, including junk. Apply fix findings with `briefs/stage8-review-fix.md`. Keep pilot verdicts unchanged as evidence; record fixes separately.

## Git coordination

Writers commit accepted content with `uv run mockgen commit <file-id>`. Critics and the parent use `uv run mockgen commit --path <exact-file> -m "<message>"`; repeat `--path` for multiple artifacts. No raw add, commit, pull, stash, reset or push during a parallel run.

`mockgen commit` and `mockgen sync` share `state/git.lock`. On a rejected push, stop dispatch and drain writers. Commit their named files with `--no-push`, resolve or release outstanding claims, and ensure the tree is clean. Then run `uv run mockgen sync --rebase` and retry the named commit to push. Routine sync uses `uv run mockgen sync`, which permits only a fast-forward. Never sync while writers are editing. Dirty trees and active claims are refused; conflicts require inspection before retrying.

Finish with `uv run mockgen sources changed` and `uv run mockgen validate --all`. Every changed/untracked document needs content review and submission against a current pack, not a render-only pass.
