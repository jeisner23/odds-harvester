#!/usr/bin/env python3
"""
Fetch upcoming fixture odds from football-data.co.uk

This script downloads the fixtures.csv from football-data.co.uk which contains
upcoming matches with betting odds from multiple bookmakers.

Output format matches what WatchyScore's odds-harvester.js expects:
{
    "matches": [...],
    "last_updated": "2026-01-16T12:00:00Z",
    "source": "football-data.co.uk"
}
"""

import io
import json
import sys
from datetime import datetime, timezone

import pandas as pd
import requests


def fetch_fixtures_csv():
    """
    Fetch the fixtures.csv from football-data.co.uk
    This contains upcoming matches with current betting odds
    """
    url = "https://www.football-data.co.uk/fixtures.csv"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    return pd.read_csv(io.StringIO(response.text))


def parse_date(date_str, time_str=None):
    """Parse date and optional time from football-data format"""
    try:
        # Date format is typically DD/MM/YY or DD/MM/YYYY
        if len(date_str) <= 8:
            date_format = "%d/%m/%y"
        else:
            date_format = "%d/%m/%Y"
        
        if time_str and pd.notna(time_str):
            dt = datetime.strptime(f"{date_str} {time_str}", f"{date_format} %H:%M")
        else:
            dt = datetime.strptime(date_str, date_format)
        
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def transform_to_watchyscore_format(df):
    """
    Transform football-data.co.uk CSV to WatchyScore format
    
    Input columns from fixtures.csv:
    - Div: League division code (E0=EPL, E1=Championship, etc.)
    - Date, Time: Match date/time
    - HomeTeam, AwayTeam: Team names
    - B365H, B365D, B365A: Bet365 1X2 odds
    - B365>2.5, B365<2.5: Bet365 O/U 2.5 goals
    - PSH, PSD, PSA: Pinnacle odds
    - MaxH, MaxD, MaxA: Market maximum odds
    - AvgH, AvgD, AvgA: Market average odds
    """
    
    # League code to name mapping
    league_map = {
        'E0': 'ENG Premier League',
        'E1': 'ENG Championship',
        'E2': 'ENG League 1',
        'E3': 'ENG League 2',
        'EC': 'ENG Conference',
        'SC0': 'SCO Premiership',
        'SC1': 'SCO Championship',
        'SC2': 'SCO League 1',
        'SC3': 'SCO League 2',
        'D1': 'DEU Bundesliga',
        'D2': 'DEU 2. Bundesliga',
        'I1': 'ITA Serie A',
        'I2': 'ITA Serie B',
        'SP1': 'ESP La Liga',
        'SP2': 'ESP Segunda',
        'F1': 'FRA Ligue 1',
        'F2': 'FRA Ligue 2',
        'N1': 'NLD Eredivisie',
        'B1': 'BEL First Division A',
        'P1': 'PRT Primeira Liga',
        'T1': 'TUR Super Lig',
        'G1': 'GRC Super League',
    }
    
    matches = []
    
    for _, row in df.iterrows():
        try:
            # Skip rows without essential data
            if pd.isna(row.get('HomeTeam')) or pd.isna(row.get('AwayTeam')):
                continue
            
            # Parse date
            date_str = row.get('Date', '')
            time_str = row.get('Time', '')
            commence_time = parse_date(str(date_str), str(time_str) if pd.notna(time_str) else None)
            
            if not commence_time:
                continue
            
            # Get league
            div = row.get('Div', '')
            league = league_map.get(div, div)
            
            # Build the match object
            match = {
                "home_team": row['HomeTeam'],
                "away_team": row['AwayTeam'],
                "commence_time": commence_time,
                "league": league,
                "league_code": div,
                "markets": {
                    "h2h": {},
                    "totals": {},
                }
            }
            
            # === 1X2 Odds ===
            # Prefer Pinnacle (sharp), fallback to Bet365, then average
            home_odds = None
            draw_odds = None
            away_odds = None
            
            # Try Pinnacle first (PSH/PSD/PSA or PH/PD/PA)
            for h, d, a in [('PSH', 'PSD', 'PSA'), ('PH', 'PD', 'PA')]:
                if h in row and pd.notna(row[h]):
                    home_odds = float(row[h])
                    draw_odds = float(row[d]) if pd.notna(row.get(d)) else None
                    away_odds = float(row[a]) if pd.notna(row.get(a)) else None
                    break
            
            # Fallback to Bet365
            if home_odds is None and 'B365H' in row and pd.notna(row['B365H']):
                home_odds = float(row['B365H'])
                draw_odds = float(row['B365D']) if pd.notna(row.get('B365D')) else None
                away_odds = float(row['B365A']) if pd.notna(row.get('B365A')) else None
            
            # Fallback to market average
            if home_odds is None and 'AvgH' in row and pd.notna(row['AvgH']):
                home_odds = float(row['AvgH'])
                draw_odds = float(row['AvgD']) if pd.notna(row.get('AvgD')) else None
                away_odds = float(row['AvgA']) if pd.notna(row.get('AvgA')) else None
            
            if home_odds and draw_odds and away_odds:
                match["markets"]["h2h"] = {
                    "home": round(home_odds, 2),
                    "draw": round(draw_odds, 2),
                    "away": round(away_odds, 2)
                }
            
            # === Over/Under 2.5 Goals ===
            over_odds = None
            under_odds = None
            
            # Try Pinnacle first
            for o, u in [('P>2.5', 'P<2.5')]:
                if o in row and pd.notna(row[o]):
                    over_odds = float(row[o])
                    under_odds = float(row[u]) if pd.notna(row.get(u)) else None
                    break
            
            # Fallback to Bet365
            if over_odds is None and 'B365>2.5' in row and pd.notna(row['B365>2.5']):
                over_odds = float(row['B365>2.5'])
                under_odds = float(row['B365<2.5']) if pd.notna(row.get('B365<2.5')) else None
            
            # Fallback to average
            if over_odds is None and 'Avg>2.5' in row and pd.notna(row['Avg>2.5']):
                over_odds = float(row['Avg>2.5'])
                under_odds = float(row['Avg<2.5']) if pd.notna(row.get('Avg<2.5')) else None
            
            if over_odds and under_odds:
                match["markets"]["totals"] = {
                    "over": round(over_odds, 2),
                    "under": round(under_odds, 2),
                    "line": 2.5
                }
            
            # Only include matches with at least h2h odds
            if match["markets"]["h2h"]:
                matches.append(match)
                
        except Exception as e:
            print(f"Warning: Error processing row: {e}", file=sys.stderr)
            continue
    
    return {
        "matches": matches,
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "football-data.co.uk",
        "match_count": len(matches)
    }


def main():
    """Main entry point"""
    print("Fetching fixtures from football-data.co.uk...", file=sys.stderr)
    
    try:
        df = fetch_fixtures_csv()
        print(f"Downloaded {len(df)} fixtures", file=sys.stderr)
        
        result = transform_to_watchyscore_format(df)
        print(f"Processed {result['match_count']} matches with odds", file=sys.stderr)
        
        # Output JSON to stdout
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
