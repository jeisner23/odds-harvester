# WatchyScore Odds Integration - football-data.co.uk

Simple, reliable betting odds for WatchyScore using football-data.co.uk's free data.

## How It Works

```
football-data.co.uk/fixtures.csv
        ↓ (GitHub Action, 3x daily)
    fetch_odds.py
        ↓
    odds.json (Gist)
        ↓ (Vercel API)
    odds-harvester.js
        ↓
    scoring-engine.js (15% of score)
```

## Coverage

| League | Code | Odds Available |
|--------|------|----------------|
| Premier League | E0 | 1X2, O/U 2.5 |
| Championship | E1 | 1X2, O/U 2.5 |
| League 1 | E2 | 1X2, O/U 2.5 |
| League 2 | E3 | 1X2, O/U 2.5 |
| Bundesliga | D1 | 1X2, O/U 2.5 |
| 2. Bundesliga | D2 | 1X2, O/U 2.5 |
| Serie A | I1 | 1X2, O/U 2.5 |
| Serie B | I2 | 1X2, O/U 2.5 |
| La Liga | SP1 | 1X2, O/U 2.5 |
| Segunda | SP2 | 1X2, O/U 2.5 |
| Ligue 1 | F1 | 1X2, O/U 2.5 |
| Ligue 2 | F2 | 1X2, O/U 2.5 |
| Eredivisie | N1 | 1X2, O/U 2.5 |
| Primeira Liga | P1 | 1X2, O/U 2.5 |
| Super Lig | T1 | 1X2, O/U 2.5 |
| Super League Greece | G1 | 1X2, O/U 2.5 |
| Scottish Premiership | SC0 | 1X2, O/U 2.5 |

## Setup

### 1. Create a Gist

1. Go to https://gist.github.com
2. Create a new secret gist with filename `odds.json`
3. Content can be empty: `{}`
4. Note the Gist ID from the URL

### 2. Add GitHub Secrets

In your repo settings → Secrets:

- `GIST_TOKEN` - Personal access token with `gist` scope
- `ODDS_GIST_ID` - The Gist ID from step 1

### 3. Deploy Files

```bash
# Copy to your repo
cp scripts/fetch_odds.py your-repo/scripts/
cp .github/workflows/fetch-odds.yml your-repo/.github/workflows/

# In WatchyScore (Vercel)
# Replace api/odds-harvester.js with the new version
```

### 4. Set Vercel Environment Variable

```
ODDS_HARVESTER_URL=https://gist.githubusercontent.com/YOUR_USERNAME/GIST_ID/raw/odds.json
```

## Update Schedule

- **football-data.co.uk updates**: Fridays (weekend games) and Tuesdays (midweek)
- **Our fetch schedule**: 6am, 12pm, 6pm UTC daily

## Why This Over OddsPortal?

| Aspect | football-data.co.uk | OddsPortal |
|--------|---------------------|------------|
| Reliability | ✅ 100% (simple CSV) | ❌ Flaky (browser scraping) |
| Speed | ✅ ~2 seconds | ❌ 30-45 minutes |
| Complexity | ✅ 100 lines Python | ❌ Playwright + retries |
| Coverage | ⚠️ 20 European leagues | ✅ 100+ global leagues |
| Cost | ✅ Free forever | ✅ Free |

## Output Format

```json
{
  "matches": [
    {
      "home_team": "Liverpool",
      "away_team": "Arsenal",
      "commence_time": "2026-01-17T15:00:00Z",
      "league": "ENG Premier League",
      "markets": {
        "h2h": { "home": 1.85, "draw": 3.40, "away": 4.20 },
        "totals": { "over": 1.90, "under": 1.90, "line": 2.5 }
      }
    }
  ],
  "last_updated": "2026-01-16T12:00:00Z",
  "source": "football-data.co.uk",
  "match_count": 150
}
```
