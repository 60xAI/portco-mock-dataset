import subprocess
import sys

import pytest
from filelock import FileLock

from conftest import run_cli


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()


def init_repo(repo):
    git(repo, "init", "-b", "main")
    git(repo, "config", "user.name", "Fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    (repo / ".gitignore").write_text("world/\nconfig/\nexemplars/\nstate/\noutput/\n")
    (repo / "unrelated.txt").write_text("original\n")
    git(repo, "add", ".gitignore", "unrelated.txt")
    git(repo, "commit", "-m", "Initial fixture")


def test_commit_artifact_leaves_other_staged_and_untracked_files_alone(repo, capsys):
    init_repo(repo)
    (repo / "critique").mkdir()
    (repo / "critique/batch.yaml").write_text("[]\n")
    (repo / "unrelated.txt").write_text("a concurrent edit\n")
    (repo / "draft.txt").write_text("another writer's draft\n")
    git(repo, "add", "unrelated.txt")
    assert run_cli(["commit", "--path", "critique/batch.yaml", "-m", "Critique batch", "--no-push"]) == 0
    assert git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD") == "critique/batch.yaml"
    assert git(repo, "diff", "--cached", "--name-only") == "unrelated.txt"
    assert (repo / "draft.txt").read_text() == "another writer's draft\n"


def test_sync_refuses_an_untracked_writer_file_then_fast_forwards_clean_tree(repo, capsys):
    init_repo(repo)
    remote = repo.parent / f"{repo.name}-remote.git"
    git(repo, "init", "--bare", str(remote))
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-u", "origin", "main")
    other = repo.parent / f"{repo.name}-other"
    git(repo, "clone", "-b", "main", str(remote), str(other))
    git(other, "config", "user.name", "Fixture")
    git(other, "config", "user.email", "fixture@example.invalid")
    (other / "draft.txt").write_text("remote version\n")
    git(other, "add", "draft.txt")
    git(other, "commit", "-m", "Remote change")
    git(other, "push")
    before = git(repo, "rev-parse", "HEAD")
    (repo / "draft.txt").write_text("writer version\n")
    assert run_cli(["sync"]) == 1
    assert "dirty" in capsys.readouterr().out.lower()
    assert git(repo, "rev-parse", "HEAD") == before
    assert (repo / "draft.txt").read_text() == "writer version\n"
    (repo / "draft.txt").unlink()
    assert run_cli(["sync"]) == 0
    assert (repo / "draft.txt").read_text() == "remote version\n"


@pytest.mark.parametrize("command", ["commit", "sync"])
def test_commit_and_sync_wait_for_the_shared_git_lock(repo, command):
    init_repo(repo)
    remote = repo.parent / f"{repo.name}-remote.git"
    git(repo, "init", "--bare", str(remote))
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "push", "-u", "origin", "main")
    if command == "commit":
        (repo / "critique").mkdir()
        (repo / "critique/batch.yaml").write_text("[]\n")
        args = ["commit", "--path", "critique/batch.yaml", "-m", "Critique", "--no-push"]
    else:
        args = ["sync"]
    script = """import sys
from pathlib import Path
from mockgen import paths
paths.ROOT = Path(sys.argv[1])
paths.STATE = paths.ROOT / 'state'
from mockgen import cli, render
print('ready', flush=True)
cli.main(sys.argv[2:])
"""
    proc = None
    try:
        with FileLock(str(repo / "state/git.lock")):
            proc = subprocess.Popen([sys.executable, "-c", script, str(repo), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            assert proc.stdout.readline().strip() == "ready"
            with pytest.raises(subprocess.TimeoutExpired):
                proc.wait(timeout=0.5)
        stdout, stderr = proc.communicate(timeout=15)
        assert proc.returncode == 0, (stdout, stderr)
    finally:
        if proc and proc.poll() is None:
            proc.kill()
            proc.communicate()


def test_sync_refuses_active_claims_even_when_tree_is_clean(repo, capsys):
    from mockgen import state
    from conftest import entry, save_entries
    init_repo(repo)
    save_entries(repo, [entry("A-001")])
    git(repo, "add", "manifest/A.yaml")
    git(repo, "commit", "-m", "Fixture manifest")
    assert state.next_batch("haiku", None, None, 1, "writer")["files"] == ["A-001"]
    assert run_cli(["sync"]) == 1
    assert "active writer claims" in capsys.readouterr().out


def test_failed_push_returns_failure_without_stashing_a_writer_draft(repo, capsys):
    init_repo(repo)
    (repo / "critique").mkdir()
    (repo / "critique/batch.yaml").write_text("[]\n")
    (repo / "draft.txt").write_text("writer version\n")
    # No origin is configured: the local commit succeeds, the push must fail.
    assert run_cli(["commit", "--path", "critique/batch.yaml", "-m", "Critique"]) == 1
    assert "push failed" in capsys.readouterr().out
    assert git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD") == "critique/batch.yaml"
    assert (repo / "draft.txt").read_text() == "writer version\n"
    assert git(repo, "stash", "list") == ""


@pytest.mark.parametrize("path", ["critique", "../outside.yaml"])
def test_artifact_commit_refuses_directories_and_paths_outside_repo(repo, path):
    init_repo(repo)
    (repo / "critique").mkdir()
    (repo / "critique/batch.yaml").write_text("[]\n")
    (repo.parent / "outside.yaml").write_text("[]\n")
    before = git(repo, "rev-parse", "HEAD")
    assert run_cli(["commit", "--path", path, "-m", "Critique", "--no-push"]) == 1
    assert git(repo, "rev-parse", "HEAD") == before
