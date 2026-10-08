# Decisions log

One line per decision taken during the build where the spec was silent or ambiguous. The spec is `docs/spec-DEV-1370.md`.

- 2026-10-08 · Build brief overrides the spec: no test suite and no code review rounds; the toolkit is throwaway internal tooling that only has to run. `submit` still runs the spec's gate checks (schema, blocklisted/unregistered names, numbers vs world, planted facts, employment-window dates, 350 cap).
- 2026-10-08 · Build brief overrides "not pushed": repo pushed to a private GitHub repo under the 60xAI org, direct to main.
- 2026-10-08 · Python pinned to 3.13 (RDKit/unstructured wheels); uv venv in `.venv` inside the repo.
- 2026-10-08 · World data stored as YAML under `world/`, one file per stage; manifest as YAML under `manifest/` (one file per firm + head office), merged by `mockgen manifest validate`.
- 2026-10-08 · Claims and generation state in SQLite (`state/claims.db`) guarded by a file lock; claim timeout 45 minutes.
