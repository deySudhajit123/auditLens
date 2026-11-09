# Day 1 Markup Notes

Measured with `python notebooks/probe.py` on 2026-11-09, on all four filings.

## Answers

| # | Question | AMD_FY2024 | AMD_FY2025 | NVDA_FY2025 | NVDA_FY2026 |
|---|---|---|---|---|---|
| 1 | Page breaks (all `<hr style="page-break-after:always">`) | 103 | 108 | 86 | 84 |
| 2 | Real heading tags (`h1`-`h6`) | 0 | 0 | 0 | 0 |
| 2 | Item headings in bold `<span>`s | 23 | 23 | 23 | 23 |
| 2 | Item matches inside tables (table of contents) | 23 | 23 | 23 | 23 |
| 3 | `<table>` elements | 73 | 69 | 68 | 64 |
| 3 | Tables with 2+ non-empty rows | 70 | 67 | 65 | 61 |
| 4 | Noise chars in `ix:header`/`ix:hidden` | 32,198 | 31,533 | 18,740 | 19,064 |
| 4 | Noise chars in `display:none` | 0 | 0 | 0 | 0 |
| 4 | `ix:*` tags | 1,506 | 1,541 | 1,473 | 1,402 |
| 5 | Clean text chars | 374,617 | 392,124 | 348,343 | 340,271 |
| 5 | Clean text as share of raw size | 17.9% | 18.0% | 16.8% | 17.3% |
| | **Page count** | **104** | **109** | **87** | **85** |

Item headings are not real heading tags in any filing, and tables are real `<table>` elements in all of them.

## Are page numbers recoverable?

**Yes, for all four filings, but the two companies number pages differently.**

| Company | Printed page number | Unnumbered pages |
|---|---|---|
| NVDA | Equals the page's position in the file | Position 1 (cover) |
| AMD | Position minus 3 | Positions 1-2 (front matter) and position 3 (table of contents) |

On every numbered page the printed number is the last line, with no gaps. On AMD's position 3 the last line looks like a page number (`101` or `106`), but it is the Signatures entry in the table of contents, so it must not be read as that page's number.

## What this means for the parser

- **Page numbering is handled by a per-filing offset.** `page_number_offset` in `data/manifest.json` is 3 for AMD and 0 for NVDA, and `parse.py` emits both `page_position_*` and `page_printed_*`. Use `page_printed_*` in citations.
- The `<hr>` breaks contain no text, so replacing them loses nothing.
- Item detection has to stay text-based, since there are no heading tags.
- AMD splits some headings across elements (`ITEM 1.` with its title separate) and uses `ITEM` in capitals with non-breaking spaces. NVDA writes `Item 1. Business` on one line. Check section titles in the parsed output for AMD.
