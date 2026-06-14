# volleyball-tabell

Generates Wikipedia `{{Volleytabell}}` markup from NVBF standings pages.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install requests beautifulsoup4 lxml
```

## Usage

```bash
.venv/bin/python3 generate_tabell.py <URL>
```

Example:

```bash
.venv/bin/python3 generate_tabell.py 'https://nvbf-web.dataproject.com/CompetitionStandings.aspx?ID=84&PID=137'
```

## Update Existing Table File

Use `update_existing_tabell.py` when you already have a wiki table file and want
to refresh the standings data.

The script:
- reads `|kilde=` from the file
- fetches standings from `RG_Standing_Main`
- reorders rows to match the source table
- updates all numeric row data
- preserves existing `{{vbk|...}}` team templates exactly as written
- creates a backup file with `.bak` extension

Usage:

```bash
.venv/bin/python3 update_existing_tabell.py <filename>
```

Example:

```bash
.venv/bin/python3 update_existing_tabell.py example-ongoing.txt
```
