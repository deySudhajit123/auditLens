# AuditLens Folder Structure

A file-by-file reference: what each file is responsible for, what it should contain, and where it stands.

Last reviewed: 2026-11-09. Update the status of a file when you implement it.

## Status at a glance

| Status | Meaning |
|---|---|
| **Done** | Has working content |
| **Blocked** | Has content or exists, but cannot do its job yet |
| **Empty** | Placeholder with no content |
| **Missing** | Part of the plan, but not in the repo |

Only these files have real content today: `README.md`, `.gitignore`, `.env.example`, `pyproject.toml`, `requirements.txt`, `auditlens/config.py`, `auditlens/ingest/parse.py`, `docs/STRUCTURE.md`, `notebooks/probe.py`, `notebooks/day1_markup_notes.md`, and the four raw filings.

"Should contain" for an Empty or Missing file describes the plan, as implied by the file's name and the project tree. Treat it as a starting brief, and correct it here when the implementation decides otherwise.

## Fix these first

| # | Problem | Fix |
|---|---|---|
| 1 | AMD's FY2025 10-K/A (listed under `related_filings`) has not been reviewed, so it is unknown whether it changes anything in the corpus | Read it on EDGAR and decide whether it belongs in the corpus |
| 2 | `auditlens/ingest/download.py` is in the plan but not in the repo | Restore it or write it |
| 3 | `LICENSE` does not exist | Choose a license and add it |
| 4 | `.github/workflows/eval.yml` is empty, so GitHub may report it as an invalid workflow | Fill it in on Day 6, or delete it until then |
| 5 | The "Project Structure" and status text in `README.md` describe the old layout | Update them and link to this file |

## How the pieces connect

```
SEC EDGAR
   │  download.py
   ▼
data/raw/*.html ──┐
                  ├─ parse.py ─► data/parsed/*.json ─► chunk.py ─► index.py
data/manifest.json┘                                                   │
                                                                      ▼
                                                                  retrieval/
                                                                      │
                                               api/ ◄── citations/ ◄── graph/

eval/ scores the retrieval and answer stages, and saves results to eval/results/.
```

Work is planned in this order:

| Day | Work |
|---|---|
| 1 | Package layout, parsing, chunking, indexing, naive retrieval |
| 2 | Retriever interface, then hybrid, rerank and contextual retrieval |
| 3 | Evaluation |
| 4 | Graph and architecture diagram |
| 5 | Citations, start of tests |
| 6 | API, Docker, CI, remaining tests |

## Repository root

| File | Responsibility | Should contain | Status |
|---|---|---|---|
| `README.md` | Entry point for the project | What AuditLens is, setup, usage, data sourcing | Done, but the layout section is out of date |
| `LICENSE` | Legal terms for reuse | The chosen license text | Missing |
| `.gitignore` | Keeps generated and private files out of Git | `data/raw/`, `data/parsed/`, `.env`, virtual environments, Python build output | Done |
| `pyproject.toml` | Makes `auditlens` an installable package | Build backend, project metadata, loose direct dependencies, package discovery limited to `auditlens*` | Done |
| `requirements.txt` | Exact, reproducible environment | Pinned versions (currently `beautifulsoup4==4.15.0`, `lxml==6.1.3`). Add a pin whenever a dependency is added to `pyproject.toml` | Done |
| `.env.example` | Lists required environment variables | Variable names with fake values, currently `SEC_USER_AGENT`. Real values go in `.env`, which is ignored by Git | Done |
| `Dockerfile` | Container image for the app | Python base image, dependency install, package copy, API start command | Empty (Day 6) |
| `docker-compose.yml` | Runs the app and its services locally | The API service, any index or database service, volumes for `data/`, the env file | Empty (Day 6) |
| `.github/workflows/eval.yml` | Runs evaluation in CI | Triggers, Python setup, dependency install, `eval/run.py`, a failure condition for score drops | Empty (Day 6) |

## `auditlens/`: the application package

Anything imported at runtime belongs here. One-off experiments go in `notebooks/`, and evaluation code goes in `eval/`.

| File | Responsibility | Should contain | Status |
|---|---|---|---|
| `__init__.py` | Marks the package | Nothing for now, later perhaps a version | Done (intentionally empty) |
| `config.py` | Single home for every tunable | Paths (`ROOT`, `DATA_DIR`, `RAW_DIR`, `PARSED_DIR`, `MANIFEST_PATH`) and thresholds (`MIN_TABLE_CHARS`). Embedding, chunking, retrieval and generation settings (`EMBED_MODEL`, `EMBED_DIM`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K`, `COLLECTION`, `QDRANT_URL`, `LLM_MODEL`). Modules import these and never hard-code their own values | Done |

Every `__init__.py` in the subpackages below is intentionally empty, and is needed for imports and package discovery.

### `auditlens/ingest/`: turn filings into searchable data

| File | Responsibility | Should contain | Status |
|---|---|---|---|
| `download.py` | Fetches 10-K filings from EDGAR | Primary-document download (not the `ix?doc=` viewer URL), the `SEC_USER_AGENT` header, polite rate limiting, a check that rejects viewer pages, manifest updates | Missing |
| `parse.py` | Converts 10-K HTML into structured sections | See [below](#parsepy-in-detail) | Done |
| `chunk.py` | Splits sections into retrieval-sized pieces | `recursive` and `semantic` strategies. Each `[TABLE]` block stays whole as its own chunk. Chunks inherit section metadata plus `chunk_id`, `chunk_index` and `chunk_strategy`, and are written to `data/parsed/chunks/<doc_id>_<strategy>.jsonl`. Run with `.venv/Scripts/python -m auditlens.ingest.chunk` | Done |
| `index.py` | Builds the search index from chunks | Embeds every chunk with `EMBED_MODEL` and rebuilds the Qdrant `COLLECTION`, with the full chunk record as each point's payload. Needs Qdrant running. Run with `.venv/Scripts/python -m auditlens.ingest.index` | Done |

#### `parse.py` in detail

Run with `python -m auditlens.ingest.parse`. It reads `data/raw/*.html` and `data/manifest.json`, and writes `data/parsed/<TICKER>_FY<year>.json`. Files with no manifest entry are skipped.

| Function | Job |
|---|---|
| `_strip_noise` | Removes inline-XBRL metadata, scripts, styles and hidden blocks |
| `_mark_pages` | Replaces page-break elements with a sentinel, falling back to `<hr>` when fewer than 5 page-break styles exist |
| `_table_to_markdown`, `_inline_tables` | Converts data tables to markdown inside `[TABLE]...[/TABLE]` and drops layout tables |
| `_page_index`, `_page_of` | Removes sentinels and maps character offsets to page numbers |
| `_find_sections` | Finds `Item N` headings; table-of-contents entries never match because they are already markdown rows |
| `parse_file` | Runs the steps above for one filing and returns `Section` objects |
| `main` | Processes every raw filing and writes the JSON output |

Each output file is a JSON list of `Section` records: `doc_id`, `ticker`, `company`, `fiscal_year`, `period_end_date`, `calendar_period`, `section_id`, `section_title`, `page_position_start`, `page_position_end`, `page_printed_start`, `page_printed_end`, `char_len`, `source_url`, `text`. Position is the page's place in the file, and printed is position minus the manifest's `page_number_offset`. Page fields are `null` when no page boundaries were detected, and printed fields are also `null` for front matter.

### `auditlens/retrieval/`: find relevant chunks

| File | Responsibility | Should contain | Status |
|---|---|---|---|
| `base.py` | The contract all retrievers share | A `Retriever` interface and a common result type, so strategies can be swapped and compared in `eval/` | Empty (Day 2) |
| `naive.py` | Baseline retriever | Plain similarity search, the score that other strategies must beat | Empty (Day 1) |
| `hybrid.py` | Combined search | Keyword and vector search with merged rankings | Empty (Day 2) |
| `rerank.py` | Improves ordering | A second-pass reranker over candidates from another retriever | Empty (Day 2) |
| `contextual.py` | Context-aware retrieval | Retrieval over chunks enriched with surrounding document context | Empty (Day 2) |

### `auditlens/graph/`: the answering workflow

| File | Responsibility | Should contain | Status |
|---|---|---|---|
| `state.py` | Data carried through the workflow | The state schema: question, retrieved chunks, draft answer, citations | Empty (Day 4) |
| `nodes.py` | Individual workflow steps | One function per step, such as retrieve, generate and validate | Empty (Day 4) |
| `build.py` | Assembles the workflow | Node wiring, edges and the compiled graph | Empty (Day 4) |

### `auditlens/citations/`: check answers against sources

| File | Responsibility | Should contain | Status |
|---|---|---|---|
| `validate.py` | Confirms each citation is real | Checks that cited chunks were retrieved and support the claim, and a clear result for failures | Empty (Day 5) |

### `auditlens/api/`: the service interface

| File | Responsibility | Should contain | Status |
|---|---|---|---|
| `main.py` | HTTP application | App setup, routes, and calls into `graph/` | Empty (Day 6) |
| `schemas.py` | Request and response shapes | Typed models for questions, answers and citations | Empty (Day 6) |

## `eval/`: measure quality

This stays outside the package because the application never imports it.

| File | Responsibility | Should contain | Status |
|---|---|---|---|
| `golden_set.jsonl` | The benchmark | One JSON object per line: a question, its expected answer and its expected sources | Empty (Day 3) |
| `run.py` | Runs the benchmark | Runs retrievers over the golden set and writes a results file | Empty (Day 3) |
| `metrics.py` | Scoring | Retrieval and answer-quality metric functions | Empty (Day 3) |
| `results/` | Score history, committed to Git | One results file per run. `.gitkeep` holds the empty folder and can go once results exist | Empty (Day 3) |

## `tests/`: automated checks

| File | Responsibility | Should contain | Status |
|---|---|---|---|
| `test_parse.py` | Protects the parser | Small HTML fixtures covering section detection, table-of-contents removal, tables and page numbers | Empty (Day 5–6) |
| `test_citations.py` | Protects citation validation | Valid, invented and mismatched citation cases | Empty (Day 5–6) |
| `test_injection.py` | Tests prompt-injection resistance | Malicious instructions planted in document text, checking the system does not obey them | Empty (Day 5–6) |

## `notebooks/`: experiments and working notes

Nothing here is imported by the application.

| File | Responsibility | Should contain | Status |
|---|---|---|---|
| `probe.py` | One-off inspection of filings | Read-only measurement of page breaks, Item headings, tables, iXBRL noise and clean text per filing | Done |
| `day1_markup_notes.md` | Findings on filing HTML | How page breaks, headings and tables appear in each company's filings | Done |
| `day1_failures.md` | Log of parsing failures | What failed, on which filing, why, and how it was handled | Empty (Day 1) |

## `data/`: inputs and generated output

| Path | Responsibility | Should contain | In Git? | Status |
|---|---|---|---|---|
| `manifest.json` | Metadata for every filing | See below | Yes | Done |
| `raw/` | Original filings | `<TICKER>_FY<YEAR>.html` primary documents | No | Done: four filings |
| `parsed/` | Output of `parse.py` | `<TICKER>_FY<year>.json` | No | Generated for all four filings |

Because `raw/` and `parsed/` are not in Git, a fresh clone needs the filings downloaded and the parser run.

Fiscal years are each company's own: AMD's ends in late December and NVIDIA's in late January. Do not compare the same `FY` label across companies without checking `period_end_date`.

### `manifest.json` format

A JSON list with one object per filing. `parse.py` requires every field below, and matches an entry to a file using the file name in `local_path`. Replace the values with the real ones for each filing:

```json
[
  {
    "ticker": "NVDA",
    "company": "NVIDIA Corporation",
    "fiscal_year": 2025,
    "period_end_date": "<YYYY-MM-DD>",
    "calendar_period": "<calendar period label>",
    "filing_date": "<YYYY-MM-DD>",
    "accession": "<EDGAR accession number>",
    "page_number_offset": 0,
    "source_url": "<EDGAR primary document URL>",
    "local_path": "data/raw/NVDA_FY2025.html"
  }
]
```

`filing_date` and `accession` are recorded for reference and are not read by `parse.py`. An entry may also have `related_filings`, a list of associated filings such as AMD's FY2025 10-K/A, each with `form`, `filing_date`, `accession` and `source_url`.

## `docs/`: project documentation

| File | Responsibility | Should contain | Status |
|---|---|---|---|
| `STRUCTURE.md` | This reference | File responsibilities and status | Done |
| `architecture.png` | System diagram | The final data flow and components | Missing (Day 4) |
| `.gitkeep` | Keeps the folder in Git | Nothing; can be removed now that the folder has a real file | Done |

## Where does new code go?

| You are adding | Put it in |
|---|---|
| A threshold, path, model name or other tunable | `auditlens/config.py` |
| A new retrieval strategy | A new file in `auditlens/retrieval/`, implementing the `base.py` interface |
| A new secret or environment variable | `.env`, plus a fake value in `.env.example` |
| A new dependency | `pyproject.toml` and a pinned line in `requirements.txt` |
| A one-off script or investigation | `notebooks/` |
| A new evaluation question | `eval/golden_set.jsonl` |
