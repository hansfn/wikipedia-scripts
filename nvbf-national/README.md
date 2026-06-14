# Scripts for generating tables for NVBF national series

Generates Wikipedia `{{Volleytabell}}` markup from NVBF standings pages.

Example: <https://no.wikipedia.org/wiki/Mal:1._divisjon_volleyball_menn_2025/26_tabell>

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install requests beautifulsoup4 lxml
```

## Scripts

### generate_table.py

The script generates a new complete `{{Volleytabell}}` block from a standings URL.

The wiki markup is sent to standard output.

Usage:

```bash
.venv/bin/python3 generate_table.py <URL>
```

Example:

```bash
.venv/bin/python3 generate_table.py 'https://nvbf-web.dataproject.com/CompetitionStandings.aspx?ID=84&PID=137'
```

### update_existing_table.py

The script updates an existing table file based on the URL given as `kilde`.

Usage:

Copy a the complete `{{Volleytabell}}` block from an edit page and save as a file.

```bash
.venv/bin/python3 update_existing_table.py <filename>
```
