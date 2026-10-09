import shutil
from pathlib import Path

import pytest

from mockgen import cli, manifest, pack, paths, render, state, submit, world


@pytest.fixture
def repo(tmp_path, monkeypatch):
    source = paths.ROOT
    manifest.entries_by_id.cache_clear()
    render.numbers.cache_clear()
    for folder in ("world", "config", "exemplars"):
        shutil.copytree(source / folder, tmp_path / folder)
    for folder in ("manifest", "numbers", "content", "state", "output"):
        (tmp_path / folder).mkdir()
    # Imported path constants all point at the same isolated fixture archive.
    for module in (paths, manifest, pack, render, state, submit, world):
        for name, value in list(vars(module).items()):
            if isinstance(value, Path) and value.is_relative_to(source):
                monkeypatch.setattr(module, name, tmp_path / value.relative_to(source))
    yield tmp_path


def entry(file_id, unit="A", tier="haiku", doc_type="wb_tracker", **kw):
    return manifest.Entry(
        id=file_id, unit=unit, root="archive", path=f"{unit}/Admin",
        filename=f"{file_id}.xlsx", format="xlsx", doc_type=doc_type,
        year=2025, era="group", template="A-G", created="2025-01-01T12:00:00",
        modified="2025-01-01T12:00:00", author="P001", last_saved_by="P001",
        finish="final", tier=tier, target_length="1 sheet", summary="A tracker.", **kw,
    )


def save_entries(repo, entries):
    import yaml
    (repo / "manifest/A.yaml").write_text(yaml.safe_dump({"files": [e.model_dump(mode="json") for e in entries]}))


def run_cli(args):
    try:
        cli.main(args)
    except SystemExit as exc:
        return exc.code
