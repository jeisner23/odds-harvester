#!/usr/bin/env python3
"""
Merge all odds JSON files from artifacts into a single organized output.
Organizes matches by day with metadata for the WatchyScore app.
"""

import json
import os
from datetime import datetime, timezone, timedelta

def parse_match(match):
    """Normalize a match from various OddsHarvester output formats."""
    if not isinstance(match, dict):
        return None
    
    # Extract team names
    home = match.get('home_team') or match.get('home') or match.get('homeTeam', '')
    away = match.get('away_team') or match.get('away') or match.get('awayTeam', '')
    
    if not home or not away:
        return None
    
    # Extract odds
    odds = {}
    
    # Check for 'odds' key
    if 'odds' in match and isinstance(match['odds'], dict):
        odds = match['odds']
    
    # Check for 'markets' key
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
    
    # Check for 'bookmakers' key (API format)
    if 'bookmakers' in match and not odds:
        for bm in match.get('bookmakers', []):
            for market in bm.get('markets', []):
                market_key = market.get('key', '')
                outcomes = market.get('outcomes', [])
                
                if market_key == 'h2h':
                    h2h = {}
                    for o in outcomes:
                        if o.get('name') == home:
                            h2h['home'] = o.get('price')
                        elif o.get('name') == away:
                            h2h['away'] = o.get('price')
                        elif o.get('name') == 'Draw':
                            h2h['draw'] = o.get('price')
                    if h2h:
                        odds['h2h'] = h2h
                        
                elif market_key == 'totals':
                    totals = {}
                    for o in outcomes:
                        if 'Over' in o.get('name', ''):
                            totals['over'] = o.get('price')
                            totals['line'] = o.get('point', 2.5)
                        elif 'Under' in o.get('name', ''):
                            totals['under'] = o.get('price')
                    if totals:
                        odds['totals'] = totals
            if odds:
                break
    
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
    
    # Get commence time
    commence = match.get('commence_time') or match.get('date') or match.get('datetime') or match.get('start_time', '')
    
    # Get league
    league = match.get('league') or match.get('competition') or match.get('tournament', 'Unknown')
    
    return {
        'home_team': home,
        'away_team': away,
        'commence_time': commence,
        'league': league,
        'markets': odds if odds else {}
    }


def main():
    all_matches = []
    seen = set()
    files_processed = 0
    errors = []
    
    # Check if artifacts directory exists
    if not os.path.exists('artifacts'):
        print("⚠️ No artifacts directory found - creating empty output")
        os.makedirs('data', exist_ok=True)
        with open('data/odds.json', 'w') as f:
            json.dump({
                'meta': {
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                    'source': 'oddsharvester',
                    'total_matches': 0,
                    'error': 'No artifacts downloaded'
                },
                'by_day': {},
                'matches': []
            }, f)
        return
    
    # Walk through all artifact directories
    for root, dirs, files in os.walk('artifacts'):
        for file in files:
            if file.endswith('.json'):
                filepath = os.path.join(root, file)
                print(f"Processing: {filepath}")
                files_processed += 1
                
                try:
                    with open(filepath, 'r') as f:
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
                    
                    for match in matches:
                        parsed = parse_match(match)
                        if not parsed:
                            continue
                        
                        # Create unique key
                        key = f"{parsed['home_team']}|{parsed['away_team']}|{parsed['commence_time']}".lower()
                        if key in seen:
                            continue
                        seen.add(key)
                        
                        all_matches.append(parsed)
                        
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")
                    continue

    # Sort by commence time
    all_matches.sort(key=lambda x: x.get('commence_time', ''))
    
    # Organize by day offset
    now = datetime.now(timezone.utc)
    today_str = now.strftime('%Y-%m-%d')
    
    by_day = {i: [] for i in range(7)}  # days 0-6
    
    for match in all_matches:
        commence = match.get('commence_time', '')
        if not commence:
            continue
            
        try:
            # Parse the commence time
            if 'T' in commence:
                match_date = commence.split('T')[0]
            else:
                match_date = commence[:10]
            
            match_dt = datetime.strptime(match_date, '%Y-%m-%d')
            today_dt = datetime.strptime(today_str, '%Y-%m-%d')
            
            day_offset = (match_dt - today_dt).days
            
            if 0 <= day_offset < 7:
                by_day[day_offset].append(match)
        except Exception:
            # If we can't parse, put in day 0
            by_day[0].append(match)
    
    # Build output structure
    output = {
        'meta': {
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'source': 'oddsharvester',
            'total_matches': len(all_matches),
            'files_processed': files_processed,
            'coverage_days': 7
        },
        'by_day': {}
    }
    
    for day_offset in range(7):
        day_matches = by_day[day_offset]
        target_date = datetime.strptime(today_str, '%Y-%m-%d')
        target_date = target_date + timedelta(days=day_offset)
        
        output['by_day'][str(day_offset)] = {
            'date': target_date.strftime('%Y-%m-%d'),
            'day_name': target_date.strftime('%A'),
            'match_count': len(day_matches),
            'matches': day_matches
        }
    
    # Also include flat list for backwards compatibility
    output['matches'] = all_matches
    
    # Add coverage info
    days_with_data = sum(1 for d in range(7) if by_day[d])
    output['meta']['days_with_data'] = days_with_data
    output['meta']['coverage_percent'] = round(days_with_data / 7 * 100)
    
    os.makedirs('data', exist_ok=True)
    with open('data/odds.json', 'w') as f:
        json.dump(output, f, separators=(',', ':'))  # Compact JSON to save space
    
    print(f"\n✅ Merged {len(all_matches)} unique matches")
    print(f"   Coverage: {days_with_data}/7 days ({output['meta']['coverage_percent']}%)")
    for day in range(7):
        count = len(by_day[day])
        status = "✓" if count > 0 else "✗"
        print(f"   {status} Day {day}: {count} matches")

if __name__ == '__main__':
    main()
