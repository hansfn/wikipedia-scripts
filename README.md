# volleyball-tabell

Generates Wikipedia `{{Volleytabell}}` markup from NVBF standings pages.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install requests beautifulsoup4 lxml
```

## Scripts

### generate_table.py

Purpose:
- generate a new `{{Volleytabell}}` block from a standings URL
- output wiki markup to standard output

Usage:

```bash
.venv/bin/python3 generate_table.py <URL>
```

Example:

```bash
.venv/bin/python3 generate_table.py 'https://nvbf-web.dataproject.com/CompetitionStandings.aspx?ID=84&PID=137'
```

### update_existing_table.py

Purpose:
- update an existing table file based on the URL given as `kilde`
- creates a backup file with `.bak` extension

Usage:

```bash
.venv/bin/python3 update_existing_table.py <filename>
```

Example:

```bash
.venv/bin/python3 update_existing_table.py example-ongoing.txt
```
