"""One-off, read-only measurement of the markup in data/raw/*.html.

Run from the repo root: python notebooks/probe.py
"""
from __future__ import annotations

import collections
import pathlib
import re

from bs4 import BeautifulSoup, NavigableString

RAW = pathlib.Path("data/raw")
SENTINEL = "@@PAGE@@"
ITEM_RE = re.compile(r"^\s*item\s+\d{1,2}[A-C]?\b", re.I)
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


def probe(path: pathlib.Path) -> None:
    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(strip=True) if soup.title else ""
    print(f"\n=== {path.name}  ({len(html):,} bytes, title={title!r})")
    if title == "XBRL Viewer":
        print("  NOT A FILING: XBRL Viewer wrapper page")
        return

    # 4. iXBRL noise, measured first because the rest runs on cleaned markup
    ix_tags = soup.find_all(re.compile(r"^ix:", re.I))
    noise = collections.Counter()
    for tag in soup.find_all(re.compile(r"^ix:(header|hidden)$", re.I)):
        noise["ix_header_hidden"] += len(tag.get_text())
        tag.decompose()
    for tag in soup.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
        noise["display_none"] += len(tag.get_text())
        tag.decompose()
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    print(f"[4] ix:* tags={len(ix_tags):,} | noise chars={dict(noise)}")

    # 3. tables
    tables = soup.find_all("table")
    data = 0
    for table in tables:
        rows = [tr for tr in table.find_all("tr") if tr.get_text(strip=True)]
        data += len(rows) >= 2
    print(f"[3] <table> total={len(tables):,} | with 2+ non-empty rows={data:,}")

    # 2. Item headings
    item_parents = collections.Counter()
    bold = 0
    samples = []
    for node in soup.find_all(string=ITEM_RE):
        if node.find_parent("table"):
            item_parents["(inside table)"] += 1
            continue
        parent = node.parent
        item_parents[parent.name] += 1
        style = (parent.get("style") or "").lower()
        bold += "font-weight:700" in style or "font-weight:bold" in style
        if len(samples) < 3:
            samples.append(f"<{parent.name}> {node.strip()[:60]!r}")
    print(f"[2] real heading tags h1-h6={len(soup.find_all(HEADINGS)):,} | "
          f"Item text parents={dict(item_parents)} | bold={bold}")
    for sample in samples:
        print(f"    {sample}")

    # 1. page breaks, and whether printed page numbers can be recovered
    styled = soup.find_all(style=re.compile(r"page-break", re.I))
    styles = collections.Counter()
    for tag in styled:
        match = re.search(r"page-break-[a-z]+\s*:\s*[a-z]+", tag["style"], re.I)
        styles[(tag.name, match.group(0).lower() if match else "?")] += 1
    inside = sum(len(tag.get_text(strip=True)) for tag in styled)
    hrs = soup.find_all("hr")
    print(f"[1] page-break styled={len(styled):,} {dict(styles)} | "
          f"text inside them={inside:,} chars | <hr>={len(hrs):,}")

    breaks = styled if len(styled) >= 5 else hrs
    for tag in breaks:
        tag.insert_before(NavigableString(f"\n{SENTINEL}\n"))
    pages = soup.get_text("\n").split(SENTINEL)
    footers = []
    for page in pages:
        lines = [line.strip() for line in page.splitlines() if line.strip()]
        footers.append(lines[-1] if lines else "")
    numeric = [int(f) for f in footers if re.fullmatch(r"\d{1,3}", f)]
    in_order = sum(b == a + 1 for a, b in zip(numeric, numeric[1:]))
    print(f"    pages={len(pages):,} | last line is a number on {len(numeric):,} | "
          f"consecutive pairs={in_order:,} | "
          f"first={numeric[:5]} last={numeric[-5:]}")
    print(f"    sample last lines: {footers[1:6]}")

    # 5. clean text
    text = re.sub(r"\s+", " ", soup.get_text(" ").replace(SENTINEL, " "))
    print(f"[5] clean text={len(text):,} chars | ratio to raw={len(text) / len(html):.1%}")


def main() -> None:
    for path in sorted(RAW.glob("*.html")):
        probe(path)


if __name__ == "__main__":
    main()
