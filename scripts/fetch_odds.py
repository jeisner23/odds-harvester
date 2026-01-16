#!/usr/bin/env python3
"""
Fetch upcoming fixture odds from football-data.co.uk
"""

import io
import json
import sys
from datetime import datetime, timezone

import pandas as pd
import requests


def fetch_fixtures_csv():
    url = "https://www.football-data.co.uk/fixtures.csv"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return pd.read_csv(io.StringIO(response.text))


def parse_date(date_str, time_str=None):
    try:
        date_format = "%d/%m/%y" if len(str(date_str)) <= 8 else "%d/%m/%Y"
        if time_str and pd.notna(time_str):
            dt = datetime.strptime(f"{date_str} {time_str}", f"{date_format} %H:%M")
        else:
            dt = datetime.strptime(str(date_str), date_format)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except:
        return None


def transform_to_json(df):
    league_map = {
        'E0': 'ENG Premier League', 'E1': 'ENG Championship', 'E2': 'ENG League 1', 'E3': 'ENG League 2',
        'SC0': 'SCO Premiership', 'SC1': 'SCO Championship',
        'D1': 'DEU Bundesliga', 'D2': 'DEU 2. Bundesliga',
        'I1': 'ITA Serie A', 'I2': 'ITA Serie B',
        'SP1': 'ESP La Liga', 'SP2': 'ESP Segunda',
        'F1': 'FRA Ligue 1', 'F2': 'FRA Ligue 2',
        'N1': 'NLD Eredivisie', 'B1': 'BEL First Division A',
        'P1': 'PRT Primeira Liga', 'T1': 'TUR Super Lig', 'G1': 'GRC Super League',
    }
    
    matches = []
    for _, row in df.iterrows():
        try:
            if pd.isna(row.get('HomeTeam')) or pd.isna(row.get('AwayTeam')):
                continue
            
            commence_time = parse_date(row.get('Date', ''), row.get('Time'))
            if not commence_time:
                continue
            
            match = {
                "home_team": row['HomeTeam'],
                "away_team": row['AwayTeam'],
                "commence_time": commence_time,
                "league": league_map.get(row.get('Div', ''), row.get('Div', '')),
                "markets": {"h2h": {}, "totals": {}}
            }
            
            # Get 1X2 odds (prefer Pinnacle, then Bet365, then average)
            for h, d, a in [('PSH', 'PSD', 'PSA'), ('B365H', 'B365D', 'B365A'), ('AvgH', 'AvgD', 'AvgA')]:
                if h in row and pd.notna(row.get(h)):
                    match["markets"]["h2h"] = {
                        "home": round(float(row[h]), 2),
                        "draw": round(float(row[d]), 2) if pd.notna(row.get(d)) else None,
                        "away": round(float(row[a]), 2) if pd.notna(row.get(a)) else None
                    }
                    break
            
            # Get O/U 2.5 odds
            for o, u in [('P>2.5', 'P<2.5'), ('B365>2.5', 'B365<2.5'), ('Avg>2.5', 'Avg<2.5')]:
                if o in row and pd.notna(row.get(o)):
                    match["markets"]["totals"] = {
                        "over": round(float(row[o]), 2),
                        "under": round(float(row[u]), 2) if pd.notna(row.get(u)) else None,
                        "line": 2.5
                    }
                    break
            
            if match["markets"]["h2h"]:
                matches.append(match)
        except Exception as e:
            continue
    
    return {
        "matches": matches,
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "football-data.co.uk",
        "match_count": len(matches)
    }


if __name__ == "__main__":
    print("Fetching fixtures...", file=sys.stderr)
    df = fetch_fixtures_csv()
    print(f"Downloaded {len(df)} rows", file=sys.stderr)
    result = transform_to_json(df)
    print(f"Processed {result['match_count']} matches with odds", file=sys.stderr)
    print(json.dumps(result, indent=2))
