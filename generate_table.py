#!/usr/bin/env python3
"""
Generate Wikipedia Volleytabell markup from nvbf-web.dataproject.com standings.

Usage: python generate_tabell.py <URL>

The URL should point to a CompetitionStandings page, e.g.:
  https://nvbf-web.dataproject.com/CompetitionStandings.aspx?ID=75&PID=122
"""

import sys
import re
import requests
from bs4 import BeautifulSoup


def get_display_name(team_name: str) -> str:
    """Strip 'VBK' and similar organizational suffixes, normalize whitespace."""
    name = re.sub(r'\s*\bVBK\b', '', team_name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def get_short_name(display_name: str) -> str:
    """
    Generate a Wikipedia-style short name from the display name.
    Strips leading club-type prefixes (TIF, SK, IK) and trailing numbers.
    """
    short = display_name
    for prefix in ('TIF ', 'SK ', 'IK '):
        if short.startswith(prefix):
            short = short[len(prefix):]
            break
    short = re.sub(r'\s+\d+$', '', short).strip()
    return short


def make_vbk(team_name: str) -> str:
    """
    Create a {{vbk|...}} template string from the team name as scraped.

    Rules:
    - Strip 'VBK' from the name to get the display name.
    - Strip leading prefixes (TIF etc.) and trailing numbers from the display
      name to get the short (Wikipedia article) name.
    - If short == display: emit {{vbk|short}}  (single param, no redundancy)
    - Otherwise:           emit {{vbk|short|display}}
    """
    display = get_display_name(team_name)
    short = get_short_name(display)
    if short == display:
        return f'{{{{vbk|{short}}}}}'
    return f'{{{{vbk|{short}|{display}}}}}'


def expand_year(year_short: str) -> str:
    """Expand a two-digit season like '24/25' to '2024/25'."""
    m = re.match(r'^(\d{2})/(\d{2})$', year_short)
    if m:
        return f'20{m.group(1)}/{m.group(2)}'
    return year_short


def build_navn(comp_title: str) -> str:
    """
    Build the Wikipedia |navn= value from the competition heading.

    Example: '1. Divisjon menn 24/25'
          -> '1. divisjon volleyball menn 2024/25 tabell'
    """
    # Expand two-digit year ranges
    navn = re.sub(r'\b(\d{2}/\d{2})\b',
                  lambda m: expand_year(m.group(1)),
                  comp_title)
    navn = navn.lower()
    # Insert 'volleyball ' right after 'divisjon '
    navn = re.sub(r'(divisjon\s+)', r'\1volleyball ', navn)
    return navn.rstrip() + ' tabell'


def get_category_year(comp_title: str) -> str:
    """Extract and expand the season year from the competition heading."""
    m = re.search(r'\b(\d{2}/\d{2})\b', comp_title)
    return expand_year(m.group(1)) if m else ''


def parse_standings(url: str) -> None:
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; WikiVolleyTabell/1.0)'}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'lxml')

    # ── Competition name ───────────────────────────────────────────────────────
    h2 = soup.find('h2')
    comp_title = h2.get_text(strip=True) if h2 else ''

    # ── Standings table ────────────────────────────────────────────────────────
    container = soup.find(id='RG_Standing_Main')
    if not container:
        print('ERROR: Could not find div#RG_Standing_Main', file=sys.stderr)
        sys.exit(1)

    table = container.find('table')
    if not table:
        print('ERROR: No <table> inside RG_Standing_Main', file=sys.stderr)
        sys.exit(1)

    # HTML row layout (verified empirically):
    #   col 0  : team name (same as col 2)
    #   col 1  : '' (empty)
    #   col 2  : team name
    #   col 3  : total points
    #   col 4  : matches played
    #   col 5  : won
    #   col 6  : lost
    #   col 7  : sets won
    #   col 8  : sets lost
    #   col 9  : points for
    #   col 10 : points against
    #   col 11+: detailed results / ratios (ignored)
    rows = []
    for tr in table.find_all('tr'):
        cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
        if len(cells) < 11:
            continue
        team_name = cells[0]
        if not team_name:
            continue
        # Skip header rows (first cell is a header string, not a number)
        try:
            total_pts = int(cells[3])
            won       = int(cells[5])
            lost      = int(cells[6])
            sets_won  = int(cells[7])
            sets_lost = int(cells[8])
            pts_for   = int(cells[9])
            pts_ag    = int(cells[10])
        except ValueError:
            continue

        rows.append(dict(
            name=team_name,
            won=won, lost=lost,
            sets_won=sets_won, sets_lost=sets_lost,
            pts_for=pts_for, pts_ag=pts_ag,
            total_pts=total_pts,
        ))

    if not rows:
        print('ERROR: No data rows found in the standings table', file=sys.stderr)
        sys.exit(1)

    # ── Format output ──────────────────────────────────────────────────────────
    vbk_exprs = [make_vbk(r['name']) for r in rows]
    # Pad the {{vbk|...}} column; minimum 34 chars to match the example style
    pad = max(34, max(len(v) for v in vbk_exprs) + 1)

    print('{{Volleytabell start}}')

    for rank, (row, vbk) in enumerate(zip(rows, vbk_exprs), start=1):
        print(
            f'{{{{Volleytabell|{rank:2d}|{vbk:<{pad}}'
            f'|{row["won"]:2d}|{row["lost"]:2d}'
            f'|{row["sets_won"]:2d}|{row["sets_lost"]:2d}'
            f'|{row["pts_for"]:4d}|{row["pts_ag"]:4d}'
            f'|{row["total_pts"]:2d}|}}}}'
        )

    navn     = build_navn(comp_title)
    cat_year = get_category_year(comp_title)

    print('{{Volleytabell footer')
    print(f'|kilde={url}')
    print(f'|navn={navn} }}}}')
    print('{{Volleytabell slutt}}<noinclude>')
    print('[[Kategori:Norske volleyballtabellmaler|{{PAGENAME}}]]')
    print(f'[[Kategori:Volleyballtabellmaler {cat_year}]]')
    print('</noinclude>')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'Usage: {sys.argv[0]} <URL>', file=sys.stderr)
        sys.exit(1)
    parse_standings(sys.argv[1])
