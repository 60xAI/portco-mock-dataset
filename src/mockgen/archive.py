"""Whole-archive validation and export."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import manifest as Mf
from .paths import ARCHIVE_ROOT, HELDBACK_ROOT, OUTPUT, CONTENT

UI_LIMIT = 30 * 1000 * 1000
INGEST_LIMIT = 60 * 1024 * 1024


def ocr_words(pdf: Path, pages: int = 1) -> int:
    tmp = Path(tempfile.mkdtemp(prefix="ocr_"))
    try:
        subprocess.run(["pdftoppm", "-r", "200", "-gray", "-f", "1", "-l", str(pages), "-png", str(pdf), str(tmp / "p")], check=True, capture_output=True, timeout=120)
        words = 0
        for img in sorted(tmp.glob("p*.png")):
            r = subprocess.run(["tesseract", str(img), "-", "--psm", "3"], capture_output=True, text=True, timeout=120)
            words += sum(1 for w in r.stdout.split() if sum(ch.isalpha() for ch in w) >= 3)
        return words
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def lo_opens(path: Path) -> bool:
    from .render import lo_convert
    tmp = Path(tempfile.mkdtemp(prefix="lochk_"))
    try:
        lo_convert(path, "pdf", tmp)
        return True
    except Exception:
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def validate_all() -> tuple[list[str], list[str]]:
    from .render import out_path
    from .submit import reopen, content_checks
    from .world import load_world
    errors, warns = Mf.validate_manifest()
    es = Mf.load_entries([])
    w = load_world([])
    for e in es:
        p = out_path(e)
        if not p.exists():
            errors.append(f"{e.id}: not rendered ({p})")
            continue
        sz = p.stat().st_size
        if sz >= UI_LIMIT or sz >= INGEST_LIMIT:
            errors.append(f"{e.id}: {sz} bytes exceeds the upload limit")
        prob = reopen(p, e.format, e.pdf_kind)
        if prob:
            errors.append(f"{e.id}: {prob}")
        if e.format in ("ppt", "xls", "doc") and not lo_opens(p):
            errors.append(f"{e.id}: LibreOffice cannot open the legacy file")
        cp = CONTENT / f"{e.id}.json"
        if cp.exists():
            fam = Mf.family(e)
            errs = content_checks(e, fam, json.loads(cp.read_text()), w)
            errors += [f"{e.id}: {x}" for x in errs]
    # stray files in output
    known = {out_path(e).resolve() for e in es}
    for root in (ARCHIVE_ROOT, HELDBACK_ROOT):
        if root.exists():
            for f in root.rglob("*"):
                if f.is_file() and f.resolve() not in known and f.name != ".DS_Store":
                    warns.append(f"stray file in output: {f}")
    return errors, warns


def export() -> str:
    from .render import out_path, set_mtime
    es = Mf.load_entries([])
    lines = ["root\tpath\tformat\tdoc_type\tunit\tbytes\tmodified"]
    for e in sorted(es, key=lambda e: (e.root, Mf.full_path(e))):
        p = out_path(e)
        sz = p.stat().st_size if p.exists() else -1
        if p.exists():
            set_mtime(p, e)  # git checkouts lose mtimes; restore the archive's dates
        lines.append(f"{e.root}\t{Mf.full_path(e)}\t{e.format}\t{e.doc_type}\t{e.unit}\t{sz}\t{e.modified.isoformat()}")
    (OUTPUT / "MANIFEST.tsv").write_text("\n".join(lines) + "\n")
    missing = sum(1 for e in es if not out_path(e).exists())
    return f"export: {ARCHIVE_ROOT} and {HELDBACK_ROOT}; listing at {OUTPUT / 'MANIFEST.tsv'} ({len(es)} files, {missing} missing)"
