"""mockgen command-line tool."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys


def _print_result(errors, warns, label):
    for w in warns:
        print(f"WARN  {w}")
    for i, e in enumerate(errors, 1):
        print(f"ERROR {i}. {e}")
    print(f"{label}: {'FAILED with %d error(s)' % len(errors) if errors else 'OK'}" + (f" ({len(warns)} warning(s))" if warns else ""))
    return 1 if errors else 0


def cmd_world(a):
    from . import world as W
    if a.action == "validate":
        errors, warns = W.validate_world(a.stage)
        return _print_result(errors, warns, f"world validate{(' --stage ' + a.stage) if a.stage else ''}")
    if a.action == "fill-staff":
        from .staff import fill_staff
        print(fill_staff(a.total))
        return 0
    if a.action == "summary":
        from .summary import world_summary
        print(world_summary())
        return 0


def cmd_manifest(a):
    from . import manifest as Mf
    if a.action == "validate":
        errors, warns = Mf.validate_manifest(a.firm)
        return _print_result(errors, warns, "manifest validate" + (f" --firm {a.firm}" if a.firm else ""))
    if a.action == "planted":
        print(Mf.planted_for(a.firm))
        return 0
    if a.action == "seed-planted":
        from .planted import build
        print(build())
        return 0
    if a.action == "merge":
        print(Mf.merge())
        return 0
    if a.action == "tree":
        print(Mf.tree(a.firm))
        return 0


def cmd_numbers(a):
    from .numbers import generate
    print(generate())
    return 0


def cmd_next(a):
    from .state import next_batch
    print(json.dumps(next_batch(a.tier, a.firm, a.type, a.batch, a.who), indent=2))
    return 0


def cmd_pack(a):
    from .pack import build_pack
    from .state import touch
    touch(a.file_id)
    try:
        print(build_pack(a.file_id))
    except ValueError as exc:
        print(exc)
        return 1
    return 0


def cmd_preflight(a):
    from .pack import preflight
    return _print_result(preflight(a.file), [], "generation preflight")


def cmd_sources(a):
    from .pack import changed_sources
    changed = changed_sources()
    print("\n".join(changed) if changed else "no source changes")
    return 1 if changed else 0


def cmd_submit(a):
    from .submit import submit
    ok, msg = submit(a.file_id, a.content, force=a.force, source_fingerprint=a.source)
    print(msg)
    return 0 if ok else 1


def cmd_release(a):
    from .state import release
    print(release(a.file_id))
    return 0


def cmd_render(a):
    from .render import render_cmd
    print(render_cmd(file_id=a.file, firm=a.firm, all_=a.all))
    return 0


def cmd_status(a):
    from .state import status
    print(status())
    return 0


def cmd_validate(a):
    from .archive import validate_all
    errors, warns = validate_all()
    return _print_result(errors, warns, "validate --all")


def cmd_golden(a):
    from .golden import build_golden
    print(build_golden())
    return 0


def git_lock():
    from filelock import FileLock
    from .paths import STATE
    STATE.mkdir(parents=True, exist_ok=True)
    return FileLock(str(STATE / "git.lock"), timeout=60)


def git_run(*args, check=True):
    from .paths import ROOT
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=check)


def cmd_sync(a):
    import time
    from . import state
    with git_lock():
        if git_run("status", "--porcelain", "--untracked-files=all").stdout.strip():
            print("sync refused: dirty tree; stop writers and commit their named files first")
            return 1
        if state.DB.exists():
            with state.db() as con:
                active = con.execute("select count(*) from files where state='claimed' and claimed_at>=?", (time.time() - state.CLAIM_TTL,)).fetchone()[0]
            if active:
                print("sync refused: active writer claims; stop writers and finish or release their claims first")
                return 1
        git_run("pull", "--rebase" if a.rebase else "--ff-only")
        print("synced")
    return 0


def cmd_commit(a):
    """Commit only named files under the same lock used by sync."""
    from pathlib import Path
    from . import manifest as Mf
    from .paths import ROOT, CONTENT
    from .render import out_path
    if bool(a.file_ids) == bool(a.path):
        print("provide file ids or exact --path files")
        return 1
    with git_lock():
        paths = []
        if a.path:
            for name in a.path:
                path = (ROOT / name).resolve()
                if (Path(name).is_absolute() or not path.is_relative_to(ROOT.resolve())
                        or ".git" in path.relative_to(ROOT.resolve()).parts or not path.is_file()):
                    print(f"not a repository file: {name}")
                    return 1
                paths.append(str(path.relative_to(ROOT.resolve())))
        else:
            es = {e.id: e for e in Mf.load_entries([])}
            for i in a.file_ids:
                e = es.get(i)
                if not e:
                    print(f"unknown id {i}")
                    return 1
                files = [CONTENT / f"{i}.json", CONTENT / f"{i}.source.json", out_path(e)]
                for x in es.values():
                    if x.pdf_kind == "export" and any(r.id == i for r in x.related):
                        files += [out_path(x), CONTENT / f"{x.id}.source.json"]
                paths += [str(p.relative_to(ROOT)) for p in files if p.exists()]
        if not paths:
            print("nothing to commit")
            return 1
        paths = sorted(set(paths))
        git_run("add", "-f", "--", *paths)
        changed = git_run("diff", "--cached", "--quiet", "--", *paths, check=False)
        if changed.returncode:
            message = a.message or f"Content: {' '.join(a.file_ids)}"
            git_run("commit", "-m", message, "--only", "--", *paths)
            print("committed named files")
        else:
            print("named files unchanged")
        if not a.no_push:
            pushed = git_run("push", "-q", check=False)
            if pushed.returncode:
                print("push failed; stop writers, commit their files, run mockgen sync --rebase, then retry")
                return 1
            print("pushed")
    return 0


def cmd_export(a):
    from .archive import export
    print(export())
    return 0


def cmd_zips(a):
    from .archive import package
    print(package())
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="mockgen")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("world")
    s.add_argument("action", choices=["validate", "fill-staff", "summary"])
    s.add_argument("--stage", choices=["group", "firms", "people", "clients", "projects", "compounds"])
    s.add_argument("--total", type=int, default=200)
    s.set_defaults(fn=cmd_world)

    s = sub.add_parser("manifest")
    s.add_argument("action", choices=["validate", "planted", "seed-planted", "merge", "tree"])
    s.add_argument("--firm")
    s.set_defaults(fn=cmd_manifest)

    s = sub.add_parser("numbers"); s.set_defaults(fn=cmd_numbers)

    s = sub.add_parser("next")
    s.add_argument("--tier", required=True, choices=["sol", "haiku", "haiku_low", "orchestrator"])
    s.add_argument("--firm"); s.add_argument("--type"); s.add_argument("--batch", type=int, default=6)
    s.add_argument("--who", default="agent")
    s.set_defaults(fn=cmd_next)

    s = sub.add_parser("pack"); s.add_argument("file_id"); s.set_defaults(fn=cmd_pack)
    s = sub.add_parser("preflight"); s.add_argument("--file"); s.set_defaults(fn=cmd_preflight)
    s = sub.add_parser("sources"); s.add_argument("action", choices=["changed"]); s.set_defaults(fn=cmd_sources)
    s = sub.add_parser("submit"); s.add_argument("file_id"); s.add_argument("content")
    s.add_argument("--source", help="fingerprint of the pack used to write/re-review this content")
    s.add_argument("--force", action="store_true", help="accept even if not claimed")
    s.set_defaults(fn=cmd_submit)
    s = sub.add_parser("release"); s.add_argument("file_id"); s.set_defaults(fn=cmd_release)
    s = sub.add_parser("render"); s.add_argument("--file"); s.add_argument("--firm"); s.add_argument("--all", action="store_true")
    s.set_defaults(fn=cmd_render)
    s = sub.add_parser("status"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("validate"); s.add_argument("--all", action="store_true", required=True); s.set_defaults(fn=cmd_validate)
    s = sub.add_parser("golden"); s.set_defaults(fn=cmd_golden)
    s = sub.add_parser("export"); s.set_defaults(fn=cmd_export)
    s = sub.add_parser("zips"); s.set_defaults(fn=cmd_zips)
    s = sub.add_parser("commit"); s.add_argument("file_ids", nargs="*"); s.add_argument("--path", action="append")
    s.add_argument("-m", "--message"); s.add_argument("--no-push", action="store_true")
    s.set_defaults(fn=cmd_commit)
    s = sub.add_parser("sync"); s.add_argument("--rebase", action="store_true")
    s.set_defaults(fn=cmd_sync)

    a = p.parse_args(argv)
    try:
        code = a.fn(a) or 0
    except subprocess.CalledProcessError as exc:
        print(f"git {exc.cmd[1]} failed (exit {exc.returncode}); inspect the repository before retrying")
        code = 1
    sys.exit(code)
