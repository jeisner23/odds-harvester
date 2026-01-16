#!/usr/bin/env python3
"""Merge all odds JSON files from artifacts into a single output file."""

import json
import os
from datetime import datetime

def main():
    all_matches = []
    seen = set()

    # Walk through all artifact directories
    for root, dirs, files in os.walk('artifacts'):
        for file in files:
            if file.endswith('.json'):
                filepath = os.path.join(root, file)
                print(f"Processing: {filepath}")
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
                        if not isinstance(match, dict):
                            continue
                        
                        # Extract team names
                        home = match.get('home_team') or match.get('home') or match.get('homeTeam', '')
                        away = match.get('away_team') or match.get('away') or match.get('awayTeam', '')
                        
                        if not home or not away:
                            continue
                        
                        # Create unique key
                        key = f"{home}|{away}".lower()
                        if key in seen:
                            continue
                        seen.add(key)
                        
                        # Extract odds - comprehensive handling
                        odds = {}
                        
                        # Check for 'odds' key
                        if 'odds' in match:
                            raw_odds = match['odds']
                            if isinstance(raw_odds, dict):
                                odds = raw_odds
                        
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
                        
                        normalized = {
                            'home_team': home,
                            'away_team': away,
                            'commence_time': commence,
                            'league': league,
                            'markets': odds if odds else {'h2h': {}}
                        }
                        
                        all_matches.append(normalized)
                        
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")
                    continue

    # Sort by commence time
    all_matches.sort(key=lambda x: x.get('commence_time', ''))

    output = {
        'updated_at': datetime.utcnow().isoformat() + 'Z',
        'source': 'oddsharvester',
        'match_count': len(all_matches),
        'matches': all_matches
    }

    os.makedirs('data', exist_ok=True)
    with open('data/odds.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Merged {len(all_matches)} unique matches")

if __name__ == '__main__':
    main()
