"""mockgen command-line tool."""
from __future__ import annotations

import argparse
import json
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
    print(build_pack(a.file_id))
    return 0


def cmd_submit(a):
    from .submit import submit
    ok, msg = submit(a.file_id, a.content, force=a.force)
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


def cmd_commit(a):
    """Commit (and push) accepted files for the given ids under a repo-wide lock; safe with parallel agents."""
    import subprocess
    from filelock import FileLock
    from . import manifest as Mf
    from .paths import ROOT, STATE, CONTENT
    from .render import out_path
    es = Mf.entries_by_id()
    paths = []
    for i in a.file_ids:
        e = es.get(i)
        if not e:
            print(f"unknown id {i}"); continue
        for p in (CONTENT / f"{i}.json", out_path(e)):
            if p.exists():
                paths.append(str(p.relative_to(ROOT)))
        for x in es.values():
            if x.pdf_kind == "export" and any(r.id == i for r in x.related) and out_path(x).exists():
                paths.append(str(out_path(x).relative_to(ROOT)))
    if not paths:
        print("nothing to commit"); return 1
    with FileLock(str(STATE / "git.lock"), timeout=600):
        subprocess.run(["git", "add", "-f", "--"] + paths, cwd=ROOT, check=True)
        r = subprocess.run(["git", "commit", "-m", a.message or f"Content: {' '.join(a.file_ids)}", "--"] + paths, cwd=ROOT, capture_output=True, text=True)
        print(r.stdout.strip().splitlines()[0] if r.stdout.strip() else r.stderr.strip()[:300])
        if not a.no_push:
            r = subprocess.run(["git", "push", "-q"], cwd=ROOT, capture_output=True, text=True)
            if r.returncode:
                subprocess.run(["git", "pull", "--rebase", "--autostash", "-q"], cwd=ROOT)
                r = subprocess.run(["git", "push", "-q"], cwd=ROOT, capture_output=True, text=True)
            print("pushed" if r.returncode == 0 else f"push failed: {r.stderr.strip()[:200]}")
    return 0


def cmd_export(a):
    from .archive import export
    print(export())
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
    s = sub.add_parser("submit"); s.add_argument("file_id"); s.add_argument("content")
    s.add_argument("--force", action="store_true", help="accept even if not claimed")
    s.set_defaults(fn=cmd_submit)
    s = sub.add_parser("release"); s.add_argument("file_id"); s.set_defaults(fn=cmd_release)
    s = sub.add_parser("render"); s.add_argument("--file"); s.add_argument("--firm"); s.add_argument("--all", action="store_true")
    s.set_defaults(fn=cmd_render)
    s = sub.add_parser("status"); s.set_defaults(fn=cmd_status)
    s = sub.add_parser("validate"); s.add_argument("--all", action="store_true", required=True); s.set_defaults(fn=cmd_validate)
    s = sub.add_parser("golden"); s.set_defaults(fn=cmd_golden)
    s = sub.add_parser("export"); s.set_defaults(fn=cmd_export)
    s = sub.add_parser("commit"); s.add_argument("file_ids", nargs="+"); s.add_argument("-m", "--message"); s.add_argument("--no-push", action="store_true")
    s.set_defaults(fn=cmd_commit)

    a = p.parse_args(argv)
    sys.exit(a.fn(a) or 0)
