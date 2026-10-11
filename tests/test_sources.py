import json

import pytest

from mockgen import world
from conftest import entry, run_cli, save_entries


@pytest.fixture
def stability_source(repo):
    w = world.load_world([])
    p = next(p for p in w.projects.values() if "stability" in p.assays and p.dates.start)
    e = entry("E-001", unit="E", tier="sol", doc_type="wb_results", projects=[p.id])
    save_entries(repo, [e])
    data = {
        "project_id": p.id, "firm": p.firm, "status": p.status,
        "values": {"price": f"{p.price.currency} {p.price.amount:,.0f}",
                   "n_compounds": str(p.n_compounds), "stability.last_timepoint_months": "0",
                   "stability.t0_assay": "100.0"},
        "tables": {"stability": {"title": "Stability", "columns": ["Condition", "Timepoint (months)", "Assay"],
                                 "rows": [["25 C", 0, "100.0"], ["40 C", 0, "100.0"]], "notes": []}},
    }
    path = repo / "numbers" / f"{p.id}.json"
    path.write_text(json.dumps(data))
    return path, data


@pytest.mark.parametrize("fault", ["cutoff", "summary", "prices"])
def test_preflight_rejects_inconsistent_sources(repo, stability_source, fault, capsys):
    path, data = stability_source
    if fault == "cutoff":
        data["tables"]["stability"]["rows"][0][1] = 999
        data["values"]["stability.last_timepoint_months"] = "999"
    elif fault == "summary":
        data["values"]["stability.last_timepoint_months"] = "6"
    else:
        data["values"]["price"] = ""
    path.write_text(json.dumps(data))
    assert run_cli(["preflight", "--file", "E-001"]) == 1
    assert fault in capsys.readouterr().out.lower()


def test_source_change_rejects_submit_before_render(repo, stability_source, capsys):
    path, data = stability_source
    assert run_cli(["pack", "E-001"]) == 0
    fingerprint = json.loads((repo / "state/packs/E-001.json").read_text())["fingerprint"]
    data["tables"]["stability"]["notes"].append("A corrected qualification.")
    path.write_text(json.dumps(data))
    draft = repo / "draft.json"
    draft.write_text(json.dumps({"family": "workbook", "summary": "An interim tracker.",
                                 "sheets": [{"name": "Tracker", "rows": [["Status", "Open"]]}]}))
    assert run_cli(["submit", "E-001", str(draft), "--force", "--source", fingerprint]) == 1
    assert "source changed" in capsys.readouterr().out.lower()
    assert list((repo / "output").rglob("*.xlsx")) == []


def test_accepted_source_receipt_flags_changed_and_untracked_content(repo, stability_source, capsys):
    path, data = stability_source
    assert run_cli(["pack", "E-001"]) == 0
    fingerprint = json.loads((repo / "state/packs/E-001.json").read_text())["fingerprint"]
    draft = repo / "draft.json"
    draft.write_text(json.dumps({"family": "workbook", "summary": "An interim tracker.",
                                 "sheets": [{"name": "Tracker", "rows": [["Status", "Open"]]}]}))
    assert run_cli(["submit", "E-001", str(draft), "--force", "--source", fingerprint]) == 0
    receipt = json.loads((repo / "content/E-001.source.json").read_text())
    assert len(receipt["fingerprint"]) == 64
    assert run_cli(["sources", "changed"]) == 0
    capsys.readouterr()
    data["tables"]["stability"]["notes"].append("A revised qualification.")
    path.write_text(json.dumps(data))
    assert run_cli(["sources", "changed"]) == 1
    assert "E-001: changed; content re-review required" in capsys.readouterr().out
    # Reading a new pack cannot silently bless already accepted content.
    assert run_cli(["pack", "E-001"]) == 0
    assert run_cli(["sources", "changed"]) == 1
    (repo / "content/E-001.source.json").unlink()
    assert run_cli(["sources", "changed"]) == 1
    assert "E-001: untracked; content re-review required" in capsys.readouterr().out


def test_another_reviewers_new_pack_cannot_bless_an_old_writers_source(repo, stability_source, capsys):
    path, data = stability_source
    assert run_cli(["pack", "E-001"]) == 0
    old = json.loads((repo / "state/packs/E-001.json").read_text())["fingerprint"]
    data["tables"]["stability"]["notes"].append("A revised qualification.")
    path.write_text(json.dumps(data))
    assert run_cli(["pack", "E-001"]) == 0
    draft = repo / "draft.json"
    draft.write_text(json.dumps({"family": "workbook", "summary": "An interim tracker.",
                                 "sheets": [{"name": "Tracker", "rows": [["Status", "Open"]]}]}))
    assert run_cli(["submit", "E-001", str(draft), "--source", old]) == 1
    assert "source changed" in capsys.readouterr().out.lower()
