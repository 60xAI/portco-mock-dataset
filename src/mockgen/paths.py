from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORLD = ROOT / "world"
NAMES = ROOT / "names"
CONFIG = ROOT / "config"
MANIFEST = ROOT / "manifest"
NUMBERS = ROOT / "numbers"
CONTENT = ROOT / "content"
STATE = ROOT / "state"
OUTPUT = ROOT / "output"
ARCHIVE_ROOT = OUTPUT / "archive"          # main archive (firms A-F + head office + Archive)
HELDBACK_ROOT = OUTPUT / "heldback_firm_G"  # firm G, uploaded later
EXEMPLARS = ROOT / "exemplars"
ASSETS = ROOT / "assets"

TODAY = date(2026, 10, 8)
SEED = 1369
