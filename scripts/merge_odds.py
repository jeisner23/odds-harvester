#!/usr/bin/env python3
"""
Incremental Odds Merger for WatchyScore

This script merges newly scraped odds data with existing odds from the Gist.
It handles single-day updates, preserving data from other days while refreshing
the scraped day's data.

Workflow:
1. Load existing odds.json (downloaded from Gist)
2. Load newly scraped day file (data/dayN.json)
3. Merge: replace that day's matches, keep other days intact
4. Output: data/odds.json for upload back to Gist
"""

import json
import os
from datetime import datetime, timezone, timedelta


def parse_match(match):
    """Normalize a match from OddsHarvester output format."""
    if not isinstance(match, dict):
        return None
    
    # Extract team names
    home = match.get('home_team') or match.get('home') or match.get('homeTeam', '')
    away = match.get('away_team') or match.get('away') or match.get('awayTeam', '')
    
    if not home or not away:
        return None
    
    # Extract odds
    odds = {}
    
    if 'odds' in match and isinstance(match['odds'], dict):
        odds = match['odds']
    
    if 'markets' in match:
        markets = match['markets']
        if isinstance(markets, dict):
            odds = markets
        elif isinstance(markets, list):
            for m in markets:
                market_name = m.get('name', '').lower()
                market_type = m.get('type', '').lower()
                
                if market_name == '1x2' or market_type == 'h2h':
                    odds['h2h'] = m.get('odds', {})
                elif 'over' in market_name or 'total' in market_type:
                    odds['totals'] = m.get('odds', {})
                elif 'btts' in market_name or 'both' in market_name:
                    odds['btts'] = m.get('odds', {})
    
    # Direct odds fields
    if not odds.get('h2h'):
        if all(k in match for k in ['home_odds', 'draw_odds', 'away_odds']):
            odds['h2h'] = {
                'home': match['home_odds'],
                'draw': match['draw_odds'],
                'away': match['away_odds']
            }
        elif '1' in match and 'X' in match and '2' in match:
            odds['h2h'] = {
                'home': match['1'],
                'draw': match['X'],
                'away': match['2']
            }
    
    commence = match.get('commence_time') or match.get('date') or match.get('datetime') or match.get('start_time', '')
    league = match.get('league') or match.get('competition') or match.get('tournament', 'Unknown')
    
    return {
        'home_team': home,
        'away_team': away,
        'commence_time': commence,
        'league': league,
        'markets': odds if odds else {}
    }


def load_existing_odds():
    """Load existing odds.json from downloaded Gist data."""
    existing_path = 'data/existing_odds.json'
    
    if not os.path.exists(existing_path):
        print("ℹ️ No existing odds data found - starting fresh")
        return None
    
    try:
        with open(existing_path, 'r') as f:
            data = json.load(f)
        print(f"✅ Loaded existing odds: {data.get('meta', {}).get('total_matches', 0)} matches")
        return data
    except Exception as e:
        print(f"⚠️ Error loading existing odds: {e}")
        return None


def load_new_day_data():
    """Load newly scraped day data from data/dayN.json files."""
    new_matches = []
    files_found = []
    
    for i in range(7):
        path = f'data/day{i}.json'
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
                # Handle different data structures
                matches = []
                if isinstance(data, list):
                    matches = data
                elif isinstance(data, dict):
                    if 'matches' in data:
                        matches = data['matches']
                    elif 'data' in data:
                        matches = data['data']
                    else:
                        matches = [data]
                
                parsed_matches = []
                for match in matches:
                    parsed = parse_match(match)
                    if parsed:
                        parsed_matches.append(parsed)
                
                if parsed_matches:
                    files_found.append(f"day{i}.json ({len(parsed_matches)} matches)")
                    new_matches.extend(parsed_matches)
                    
            except Exception as e:
                print(f"⚠️ Error loading {path}: {e}")
    
    if files_found:
        print(f"📁 Loaded new data: {', '.join(files_found)}")
    
    return new_matches


def get_day_offset(commence_time, today_str):
    """Calculate day offset from today for a match."""
    if not commence_time:
        return -1
    
    try:
        if 'T' in commence_time:
            match_date = commence_time.split('T')[0]
        else:
            match_date = commence_time[:10]
        
        match_dt = datetime.strptime(match_date, '%Y-%m-%d')
        today_dt = datetime.strptime(today_str, '%Y-%m-%d')
        
        return (match_dt - today_dt).days
    except Exception:
        return -1


def main():
    os.makedirs('data', exist_ok=True)
    
    now = datetime.now(timezone.utc)
    today_str = now.strftime('%Y-%m-%d')
    
    # Load existing data
    existing = load_existing_odds()
    
    # Load new scraped data
    new_matches = load_new_day_data()
    
    if not new_matches and not existing:
        print("❌ No data available - creating empty output")
        output = {
            'meta': {
                'updated_at': now.isoformat(),
                'source': 'oddsharvester',
                'total_matches': 0,
                'error': 'No data available'
            },
            'by_day': {},
            'matches': []
        }
        with open('data/odds.json', 'w') as f:
            json.dump(output, f, separators=(',', ':'))
        return
    
    # Determine which days have new data
    new_days = set()
    for match in new_matches:
        day = get_day_offset(match.get('commence_time', ''), today_str)
        if 0 <= day < 7:
            new_days.add(day)
    
    print(f"📅 New data covers days: {sorted(new_days) if new_days else 'none'}")
    
    # Build merged data structure
    by_day = {i: [] for i in range(7)}
    seen = set()
    
    # First, add new matches (they take priority for refreshed days)
    for match in new_matches:
        day = get_day_offset(match.get('commence_time', ''), today_str)
        if 0 <= day < 7:
            key = f"{match['home_team']}|{match['away_team']}|{match['commence_time']}".lower()
            if key not in seen:
                seen.add(key)
                by_day[day].append(match)
    
    # Then, add existing matches for days we DIDN'T just scrape
    if existing and 'by_day' in existing:
        # Recalculate day offsets for existing data (dates may have shifted)
        for day_str, day_data in existing.get('by_day', {}).items():
            old_day = int(day_str)
            
            for match in day_data.get('matches', []):
                # Recalculate what day this match is NOW
                current_day = get_day_offset(match.get('commence_time', ''), today_str)
                
                # Skip if outside our window
                if current_day < 0 or current_day >= 7:
                    continue
                
                # Skip if we just refreshed this day
                if current_day in new_days:
                    continue
                
                key = f"{match['home_team']}|{match['away_team']}|{match['commence_time']}".lower()
                if key not in seen:
                    seen.add(key)
                    by_day[current_day].append(match)
    
    # Build output structure
    total_matches = sum(len(matches) for matches in by_day.values())
    days_with_data = sum(1 for matches in by_day.values() if matches)
    
    output = {
        'meta': {
            'updated_at': now.isoformat(),
            'source': 'oddsharvester',
            'total_matches': total_matches,
            'coverage_days': 7,
            'days_with_data': days_with_data,
            'last_refreshed_days': sorted(list(new_days)) if new_days else []
        },
        'by_day': {}
    }
    
    all_matches = []
    for day_offset in range(7):
        day_matches = by_day[day_offset]
        target_date = datetime.strptime(today_str, '%Y-%m-%d') + timedelta(days=day_offset)
        
        output['by_day'][str(day_offset)] = {
            'date': target_date.strftime('%Y-%m-%d'),
            'day_name': target_date.strftime('%A'),
            'match_count': len(day_matches),
            'matches': day_matches
        }
        
        all_matches.extend(day_matches)
    
    # Sort all matches by commence time
    all_matches.sort(key=lambda x: x.get('commence_time', ''))
    output['matches'] = all_matches
    
    # Write output
    with open('data/odds.json', 'w') as f:
        json.dump(output, f, separators=(',', ':'))
    
    # Summary
    print(f"\n{'='*50}")
    print("           MERGE SUMMARY")
    print('='*50)
    print(f"Total matches: {total_matches}")
    print(f"Coverage: {days_with_data}/7 days")
    print("")
    for day in range(7):
        count = len(by_day[day])
        refreshed = "🔄" if day in new_days else "  "
        status = "✓" if count > 0 else "✗"
        print(f"  {refreshed} {status} Day {day}: {count:3d} matches")
    print('='*50)


if __name__ == '__main__':
    main()
