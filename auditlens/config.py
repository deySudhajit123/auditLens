"""Every tunable, in one place."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Paths
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PARSED_DIR = DATA_DIR / "parsed"
MANIFEST_PATH = DATA_DIR / "manifest.json"

# Parsing
MIN_SECTION_CHARS = 1000   # table-of-contents entries sit closer than this
MIN_TABLE_CHARS = 40       # below this a <table> is layout, not data
