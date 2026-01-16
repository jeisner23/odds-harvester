#!/usr/bin/env python3
"""
Merge today and tomorrow's odds into a single JSON file
for WatchyScore consumption.
"""

import json
import os
from datetime import datetime, timezone

DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "odds.json")

def load_json_safe(filepath):
    """Load JSON file, return empty list if not found or invalid."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            # Handle both list and dict formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get('matches', data.get('events', data.get('data', [])))
            return []
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return []

def normalize_match(match):
    """
    Normalize match data to a consistent format for WatchyScore.
    
    Output format:
    {
        "home_team": "Team A",
        "away_team": "Team B", 
        "commence_time": "2024-01-16T15:00:00Z",
        "league": "England - Premier League",
        "markets": {
            "h2h": {
                "home": 1.85,
                "draw": 3.50,
                "away": 4.20
            }
        }
    }
    """
    normalized = {
        "home_team": match.get("home_team") or match.get("homeTeam") or match.get("home", {}).get("name", ""),
        "away_team": match.get("away_team") or match.get("awayTeam") or match.get("away", {}).get("name", ""),
        "commence_time": match.get("commence_time") or match.get("start_time") or match.get("date", ""),
        "league": match.get("league") or match.get("competition") or match.get("tournament", ""),
    }
    
    # Extract odds - handle various formats from OddsHarvester
    markets = {}
    
    # Format 1: Direct odds object
    if "odds" in match:
        odds = match["odds"]
        if isinstance(odds, dict):
            # Check for 1x2 / h2h market
            h2h = {}
            if "1" in odds or "home" in odds:
                h2h["home"] = float(odds.get("1") or odds.get("home") or 0)
            if "X" in odds or "draw" in odds:
                h2h["draw"] = float(odds.get("X") or odds.get("draw") or 0)
            if "2" in odds or "away" in odds:
                h2h["away"] = float(odds.get("2") or odds.get("away") or 0)
            if h2h.get("home") and h2h.get("away"):
                markets["h2h"] = h2h
    
    # Format 2: Markets array from OddsHarvester
    if "markets" in match:
        for market in match.get("markets", []):
            market_key = market.get("key") or market.get("name", "").lower()
            
            if market_key in ["1x2", "h2h", "match_winner", "fulltime_result"]:
                h2h = {}
                for outcome in market.get("outcomes", []):
                    name = str(outcome.get("name", "")).lower()
                    price = outcome.get("price") or outcome.get("odd") or outcome.get("odds")
                    if price:
                        price = float(price)
                        if name in ["1", "home"] or "home" in name:
                            h2h["home"] = price
                        elif name in ["x", "draw", "tie"]:
                            h2h["draw"] = price
                        elif name in ["2", "away"] or "away" in name:
                            h2h["away"] = price
                if h2h.get("home") and h2h.get("away"):
                    markets["h2h"] = h2h
            
            elif market_key in ["totals", "over_under", "goals"]:
                ou = {}
                for outcome in market.get("outcomes", []):
                    name = str(outcome.get("name", "")).lower()
                    price = outcome.get("price") or outcome.get("odd")
                    point = outcome.get("point") or outcome.get("line", 2.5)
                    if price and point == 2.5:
                        if "over" in name:
                            ou["over"] = float(price)
                        elif "under" in name:
                            ou["under"] = float(price)
                if ou.get("over") and ou.get("under"):
                    markets["totals"] = ou
            
            elif market_key in ["btts", "both_teams_to_score"]:
                btts = {}
                for outcome in market.get("outcomes", []):
                    name = str(outcome.get("name", "")).lower()
                    price = outcome.get("price") or outcome.get("odd")
                    if price:
                        if name in ["yes", "y"]:
                            btts["yes"] = float(price)
                        elif name in ["no", "n"]:
                            btts["no"] = float(price)
                if btts.get("yes") and btts.get("no"):
                    markets["btts"] = btts
    
    # Format 3: Bookmakers array (The Odds API style)
    if "bookmakers" in match:
        for bookmaker in match.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                if market_key == "h2h" and "h2h" not in markets:
                    h2h = {}
                    for outcome in market.get("outcomes", []):
                        name = outcome.get("name", "")
                        price = outcome.get("price")
                        if name == match.get("home_team"):
                            h2h["home"] = price
                        elif name == match.get("away_team"):
                            h2h["away"] = price
                        elif name.lower() == "draw":
                            h2h["draw"] = price
                    if h2h.get("home") and h2h.get("away"):
                        markets["h2h"] = h2h
                        break  # Use first bookmaker with valid odds
    
    normalized["markets"] = markets
    return normalized

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Load scraped data
    today_matches = load_json_safe(os.path.join(DATA_DIR, "today.json"))
    tomorrow_matches = load_json_safe(os.path.join(DATA_DIR, "tomorrow.json"))
    
    print(f"Loaded {len(today_matches)} matches from today")
    print(f"Loaded {len(tomorrow_matches)} matches from tomorrow")
    
    # Combine and normalize
    all_matches = today_matches + tomorrow_matches
    normalized = []
    
    for match in all_matches:
        try:
            norm = normalize_match(match)
            # Only include if we have valid team names and odds
            if norm["home_team"] and norm["away_team"] and norm["markets"].get("h2h"):
                normalized.append(norm)
        except Exception as e:
            print(f"Warning: Failed to normalize match: {e}")
    
    print(f"Normalized {len(normalized)} matches with valid odds")
    
    # Create output
    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "oddsportal.com",
        "match_count": len(normalized),
        "matches": normalized
    }
    
    # Write output
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Wrote {len(normalized)} matches to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
