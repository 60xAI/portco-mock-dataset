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
    s.add_argument("action", choices=["validate", "planted", "merge", "tree"])
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

    a = p.parse_args(argv)
    sys.exit(a.fn(a) or 0)
