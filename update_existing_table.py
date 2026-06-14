#!/usr/bin/env python3
"""
Update an existing Wikipedia volleyball table file from its |kilde= URL.

Behavior:
- Reads the input file
- Extracts the standings URL from the |kilde= line
- Fetches standings from div#RG_Standing_Main
- Reorders and updates table rows to match standings order and values
- Preserves each existing {{vbk|...}} expression exactly as-is
- Creates a backup: <filename>.bak
- Writes the updated file in-place

Usage:
  python update_existing_tabell.py <filename>
"""

import re
import sys
import shutil
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup


ROW_RE = re.compile(
    r"^\{\{Volleytabell\|\s*\d+\|(.*?)"
    r"\|\s*\d+\|\s*\d+\|\s*\d+\|\s*\d+\|\s*\d+\|\s*\d+\|\s*\d+(?:\|.*?)?\|\}\}\s*$"
)
KILDE_RE = re.compile(r"^\|kilde=(\S+)\s*$")


@dataclass
class StandingRow:
    source_name: str
    won: int
    lost: int
    sets_won: int
    sets_lost: int
    pts_for: int
    pts_against: int
    total_pts: int


def normalize_key(name: str) -> str:
    """Normalize team names for robust matching."""
    # Remove explicit 'VBK' token and normalize punctuation/spacing.
    name = re.sub(r"\bVBK\b", "", name, flags=re.IGNORECASE)
    name = name.casefold()
    return re.sub(r"[\W_]+", "", name, flags=re.UNICODE)


def get_display_name(source_name: str) -> str:
    """Strip standalone 'VBK' from scraped source names."""
    name = re.sub(r"\s*\bVBK\b", "", source_name)
    return re.sub(r"\s+", " ", name).strip()


def parse_vbk_display(vbk_expr: str) -> str:
    """
    Resolve display name from an existing {{vbk|...}} expression.

    - {{vbk|Short}} -> display is Short
    - {{vbk|Short|Display}} -> display is Display
    """
    m = re.fullmatch(r"\{\{vbk\|(.*?)\}\}", vbk_expr.strip())
    if not m:
        return vbk_expr.strip()

    parts = [p.strip() for p in m.group(1).split("|")]
    if len(parts) >= 2:
        return parts[1]
    return parts[0] if parts else ""


def fetch_standings(url: str) -> list[StandingRow]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; WikiVolleyTabellUpdater/1.0)"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    container = soup.find(id="RG_Standing_Main")
    if not container:
        raise RuntimeError("Could not find div#RG_Standing_Main")

    table = container.find("table")
    if not table:
        raise RuntimeError("No <table> found inside RG_Standing_Main")

    rows: list[StandingRow] = []
    for tr in table.find_all("tr"):
        cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 11:
            continue

        team_name = cells[0]
        if not team_name:
            continue

        try:
            total_pts = int(cells[3])
            won = int(cells[5])
            lost = int(cells[6])
            sets_won = int(cells[7])
            sets_lost = int(cells[8])
            pts_for = int(cells[9])
            pts_against = int(cells[10])
        except ValueError:
            continue

        rows.append(
            StandingRow(
                source_name=team_name,
                won=won,
                lost=lost,
                sets_won=sets_won,
                sets_lost=sets_lost,
                pts_for=pts_for,
                pts_against=pts_against,
                total_pts=total_pts,
            )
        )

    if not rows:
        raise RuntimeError("No standings rows found in table")

    return rows


def extract_kilde(lines: list[str]) -> str:
    for line in lines:
        m = KILDE_RE.match(line.strip())
        if m:
            return m.group(1)
    raise RuntimeError("Could not find a '|kilde=<url>' line in file")


def extract_existing_vbk_map(lines: list[str]) -> dict[str, str]:
    """Map normalized team key -> original {{vbk|...}} expression from file."""
    mapping: dict[str, str] = {}

    for line in lines:
        m = ROW_RE.match(line.strip())
        if not m:
            continue

        vbk_expr = m.group(1).strip()
        display = parse_vbk_display(vbk_expr)
        key = normalize_key(display)

        if key:
            mapping[key] = vbk_expr

    if not mapping:
        raise RuntimeError("No existing '{{Volleytabell|...}}' team rows found")

    return mapping


def build_new_row_lines(standings: list[StandingRow], vbk_map: dict[str, str]) -> list[str]:
    vbk_exprs: list[str] = []
    missing: list[str] = []

    for row in standings:
        display = get_display_name(row.source_name)
        key = normalize_key(display)
        vbk_expr = vbk_map.get(key)
        if not vbk_expr:
            missing.append(row.source_name)
            vbk_exprs.append("{{vbk|" + display + "}}")
        else:
            vbk_exprs.append(vbk_expr)

    if missing:
        missing_str = ", ".join(missing)
        raise RuntimeError(
            "Could not match these teams to existing {{vbk|...}} rows: " + missing_str
        )

    pad = max(34, max(len(v) for v in vbk_exprs) + 1)

    new_lines: list[str] = []
    for rank, (row, vbk) in enumerate(zip(standings, vbk_exprs), start=1):
        farge = "|farge=fff" if rank <= 3 else ""
        row_end = "}}" if rank <= 3 else "|}}"
        new_lines.append(
            "{{Volleytabell|"
            + f"{rank:2d}|{vbk:<{pad}}"
            + f"|{row.won:2d}|{row.lost:2d}"
            + f"|{row.sets_won:2d}|{row.sets_lost:2d}"
            + f"|{row.pts_for:4d}|{row.pts_against:4d}"
            + f"|{row.total_pts:2d}{farge}{row_end}"
        )

    return new_lines


def replace_table_rows(lines: list[str], new_row_lines: list[str]) -> list[str]:
    row_indices = [
        i for i, line in enumerate(lines)
        if ROW_RE.match(line.strip())
    ]
    if not row_indices:
        raise RuntimeError("No existing '{{Volleytabell|...}}' rows found to replace")

    first = row_indices[0]
    last = row_indices[-1]

    # Replace the entire existing row block.
    return lines[:first] + new_row_lines + lines[last + 1:]


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <filename>", file=sys.stderr)
        return 1

    filename = sys.argv[1]

    with open(filename, "r", encoding="utf-8") as f:
        original_text = f.read()

    lines = original_text.splitlines()

    kilde_url = extract_kilde(lines)
    standings = fetch_standings(kilde_url)
    vbk_map = extract_existing_vbk_map(lines)

    new_rows = build_new_row_lines(standings, vbk_map)
    updated_lines = replace_table_rows(lines, new_rows)

    backup_path = filename + ".bak"
    shutil.copyfile(filename, backup_path)

    with open(filename, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(updated_lines) + "\n")

    print(f"Updated {filename}")
    print(f"Backup  {backup_path}")
    print(f"Source  {kilde_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
