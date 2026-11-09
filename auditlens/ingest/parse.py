"""Parse EDGAR 10-K HTML into sections with page numbers and markdown tables.

Input:  data/raw/*.html  +  data/manifest.json
Output: data/parsed/<TICKER>_FY<year>.json

Run: python -m auditlens.ingest.parse
"""
from __future__ import annotations

import json
import pathlib
import re
from dataclasses import dataclass, asdict

from bs4 import BeautifulSoup, NavigableString

from auditlens.config import (
    MANIFEST_PATH as MANIFEST,
    MIN_TABLE_CHARS,
    PARSED_DIR as PARSED,
    RAW_DIR as RAW,
)

PAGEBREAK = "@@PAGEBREAK@@"

ITEM_RE = re.compile(
    r"^\s*item\s+(\d{1,2}[A-C]?)\s*[\.\:\-–—]?\s*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class Section:
    doc_id: str
    ticker: str
    company: str
    fiscal_year: str
    period_end_date: str
    calendar_period: str
    section_id: str          # "Item 1A"
    section_title: str       # "Risk Factors"
    page_position_start: int | None   # position in the file, 1-based
    page_position_end: int | None
    page_printed_start: int | None    # number printed in the filing
    page_printed_end: int | None
    char_len: int
    source_url: str
    text: str


# ---------------- cleaning ----------------

def _strip_noise(soup: BeautifulSoup) -> int:
    """Drop inline-XBRL metadata, scripts, styles and display:none blocks."""
    removed = 0
    for tag in soup.find_all(re.compile(r"^ix:(header|hidden)$", re.I)):
        removed += len(tag.get_text())
        tag.decompose()
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    for tag in soup.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
        removed += len(tag.get_text())
        tag.decompose()
    return removed


# ---------------- page boundaries ----------------

def _mark_pages(soup: BeautifulSoup) -> tuple[int, str]:
    """Replace page-break elements with a sentinel. Returns (count, mechanism)."""
    breaks = soup.find_all(style=re.compile(r"page-break", re.I))
    mechanism = "page-break-style"
    if len(breaks) < 5:
        breaks = soup.find_all("hr")
        mechanism = "hr"
    for tag in breaks:
        tag.replace_with(NavigableString(f"\n{PAGEBREAK}\n"))
    return len(breaks), mechanism


# ---------------- tables ----------------

def _table_to_markdown(table) -> str:
    rows = []
    for tr in table.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if any(cells):
            rows.append(cells)
    if len(rows) < 2:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    md = "\n".join(out)
    return md if len(md) >= MIN_TABLE_CHARS else ""


def _inline_tables(soup: BeautifulSoup) -> int:
    kept = 0
    for table in soup.find_all("table"):
        md = _table_to_markdown(table)
        if md:
            kept += 1
            table.replace_with(NavigableString(f"\n\n[TABLE]\n{md}\n[/TABLE]\n\n"))
        else:
            table.decompose()
    return kept


# ---------------- sectioning ----------------

def _page_index(text: str) -> tuple[str, list[int]]:
    """Strip sentinels; return clean text + char offset where each page starts."""
    parts = text.split(PAGEBREAK)
    offsets, cursor = [], 0
    for part in parts:
        offsets.append(cursor)
        cursor += len(part)
    return "".join(parts), offsets


def _page_of(offset: int, offsets: list[int]) -> int | None:
    if len(offsets) <= 1:
        return None
    page = 1
    for i, start in enumerate(offsets):
        if start <= offset:
            page = i + 1
        else:
            break
    return page


def _printed_page(position: int | None, offset: int) -> int | None:
    """Position minus the filing's offset; None for front matter."""
    if position is None or position - offset < 1:
        return None
    return position - offset


def _find_sections(text: str) -> list[tuple[int, str, str]]:
    """Return (offset, item_id, title).

    Table-of-contents entries never match: _inline_tables has already turned
    them into markdown rows, which start with "|".
    """
    return [(m.start(), m.group(1).upper(), m.group(2).strip(" .:-–—"))
            for m in ITEM_RE.finditer(text)]


# ---------------- driver ----------------

def parse_file(path: pathlib.Path, meta: dict) -> list[Section]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "lxml")
    noise = _strip_noise(soup)
    n_breaks, mechanism = _mark_pages(soup)
    n_tables = _inline_tables(soup)

    raw = soup.get_text("\n")
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    raw = re.sub(r"[ \t]{2,}", " ", raw)
    text, offsets = _page_index(raw)

    hits = _find_sections(text)
    print(f"  {path.name}: pages={n_breaks} via {mechanism} | tables={n_tables} "
          f"| noise={noise:,} | text={len(text):,} | sections={len(hits)}")
    if n_breaks < 5:
        print("  !! no page boundaries detected — page metadata will be null")

    doc_id = f"{meta['ticker']}_FY{meta['fiscal_year']}"
    sections = []
    for i, (offset, item_id, title) in enumerate(hits):
        end = hits[i + 1][0] if i + 1 < len(hits) else len(text)
        body = text[offset:end].strip()
        position_start = _page_of(offset, offsets)
        position_end = _page_of(end - 1, offsets)
        sections.append(Section(
            doc_id=doc_id,
            ticker=meta["ticker"],
            company=meta["company"],
            fiscal_year=str(meta["fiscal_year"]),
            period_end_date=meta["period_end_date"],
            calendar_period=meta["calendar_period"],
            section_id=f"Item {item_id}",
            section_title=title,
            page_position_start=position_start,
            page_position_end=position_end,
            page_printed_start=_printed_page(position_start, meta["page_number_offset"]),
            page_printed_end=_printed_page(position_end, meta["page_number_offset"]),
            char_len=len(body),
            source_url=meta["source_url"],
            text=body,
        ))
    return sections


def main() -> None:
    PARSED.mkdir(parents=True, exist_ok=True)
    manifest = {pathlib.Path(m["local_path"]).name: m
                for m in json.loads(MANIFEST.read_text())}

    for path in sorted(RAW.glob("*.html")):
        meta = manifest.get(path.name)
        if not meta:
            print(f"  SKIP {path.name}: no manifest entry")
            continue
        sections = parse_file(path, meta)
        out = PARSED / f"{meta['ticker']}_FY{meta['fiscal_year']}.json"
        out.write_text(json.dumps([asdict(s) for s in sections], indent=2))
        print(f"  -> {out}")


if __name__ == "__main__":
    main()