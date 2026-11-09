# AuditLens

AuditLens is a project for analyzing SEC annual reports (Form 10-K) filed by public companies. Its current focus is semiconductor companies: AMD and NVIDIA.

> **Status:** Early stage. The repository currently contains only raw filing data. No analysis code has been added yet.

## Project Structure

```
AuditLens/
├── data/
│   └── raw/                  # Original 10-K filings downloaded from SEC EDGAR
│       ├── AMD_FY2024.html
│       ├── AMD_FY2025.html
│       ├── NVDA_FY2025.html
│       └── NVDA_FY2026.html
└── README.md
```

## Data

Each filing in `data/raw/` is named `<TICKER>_FY<YEAR>.html`, where `<YEAR>` is the company's own fiscal year. The two companies use different fiscal calendars:

| Ticker | Company                | Fiscal year ends                             |
| ------ | ---------------------- | -------------------------------------------- |
| AMD    | Advanced Micro Devices | Late December                                |
| NVDA   | NVIDIA Corporation     | Late January (e.g. FY2025 ended 26 Jan 2025) |

Filings come from [SEC EDGAR](https://www.sec.gov/edgar/search/) in Inline XBRL (iXBRL) format, so the financial values in them are tagged and can be read by a machine.

### Downloading filings

1. Search for the company on [EDGAR full-text search](https://efts.sec.gov/LATEST/search-index?q=&forms=10-K) or open its filing index, for example `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=<CIK>&type=10-K`.
2. Open the 10-K filing and download the **primary document** (`<ticker>-<yyyymmdd>.htm`). Do not save the page that opens at `sec.gov/ix?doc=...`. That URL loads the XBRL viewer, which is only a wrapper around the filing.
3. Save the file to `data/raw/` using the naming convention above.

SEC requires automated requests to send a `User-Agent` header that identifies you, for example `AuditLens your-email@example.com`.

## Roadmap

- [ ] Parse iXBRL filings and extract key financial facts
- [ ] Normalize metrics across companies with different fiscal calendars
- [ ] Compare companies and track changes from year to year
