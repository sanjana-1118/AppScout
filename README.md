# AppScout — Single-App Experiment (Phase 1)

A minimal, single-request experiment to inspect what the Shopify App Store
actually returns for a given app page URL — before any extraction logic is built.

---

## Goals of Phase 1

- Make **one** HTTP GET request to a target Shopify App Store URL.
- Save the **raw response** (headers + body) to disk.
- Print a **human-readable inspection summary** to stdout.
- Produce **zero infrastructure**: no database, no queue, no browser, no Docker.

Phase 1 deliberately does **not** extract structured data. The raw response must
be reviewed first so that extraction logic can be grounded in reality.

---

## Project Layout

```
AppScout/
├── README.md
├── requirements.txt
├── experiment/
│   ├── __init__.py
│   ├── acquire.py          # HTTP request + save raw response
│   ├── inspect_response.py # Human-readable inspection of saved response
│   ├── models.py           # Lightweight dataclasses (RawResponse, InspectionReport)
│   └── run_experiment.py   # CLI entry-point
├── data/
│   └── raw/                # Raw saved responses land here
└── output/                 # Inspection reports land here
```

---

## Setup

### 1. Create and activate the virtual environment

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running the Experiment

```bash
python -m experiment.run_experiment --url <shopify-app-page-url>
```

**Example:**
```bash
python -m experiment.run_experiment --url "https://apps.shopify.com/some-app"
```

### Optional flags

| Flag | Default | Description |
|------|---------|-------------|
| `--url` | *(required)* | Full URL of the Shopify App Store page |
| `--output-dir` | `output` | Directory where the inspection report is written |
| `--raw-dir` | `data/raw` | Directory where the raw HTTP response is saved |
| `--timeout` | `30` | Request timeout in seconds |

---

## Output Files

After a successful run two files are written:

| File | Description |
|------|-------------|
| `data/raw/<slug>_<timestamp>.json` | Raw response: status, headers, body (text) |
| `output/<slug>_<timestamp>_inspection.txt` | Human-readable inspection report |

Both files use the app slug derived from the URL and a UTC timestamp so that
multiple runs never overwrite each other.

---

## Constraints (by design)

- **One request only.** No retries.
- **No headless browsers.** Plain `requests` only.
- **No CAPTCHA bypass / rate-limit bypass.**
- **No infrastructure.** No Redis, Celery, Docker, or databases.
- **Acquire ≠ Inspect.** `acquire.py` saves the response; `inspect_response.py`
  reads the saved file. They are intentionally decoupled.

---

## Next Steps (Phase 2 — not yet implemented)

After reviewing the inspection output, `extract.py` and `validate.py` will be
added to parse structured fields from the raw response.
