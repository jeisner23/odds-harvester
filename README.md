# OddsHarvester for WatchyScore

Automated soccer odds scraping using GitHub Actions. Runs every 3 hours and publishes odds data to a GitHub Gist that WatchyScore can consume.

## Architecture

```
┌──────────────────┐      ┌─────────────────┐      ┌──────────────┐
│ GitHub Actions   │─────▶│ GitHub Gist     │─────▶│ WatchyScore  │
│ (every 3 hours)  │      │ (odds.json)     │      │ (Vercel)     │
└──────────────────┘      └─────────────────┘      └──────────────┘
```

## Setup Guide (15 minutes)

### Step 1: Create Your Repository

1. Create a new **private** GitHub repo called `odds-harvester`
2. Clone it locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/odds-harvester.git
   cd odds-harvester
   ```

3. Copy the OddsHarvester source code into it:
   - Extract the OddsHarvester-master.zip
   - Copy the `src/` folder into your repo
   - Copy `pyproject.toml` (optional)

4. Add the workflow and scripts from this setup:
   ```
   odds-harvester/
   ├── .github/
   │   └── workflows/
   │       └── scrape-odds.yml    ← GitHub Actions workflow
   ├── scripts/
   │   └── merge_odds.py          ← Combines daily data
   ├── data/                      ← Created automatically
   │   └── .gitkeep
   ├── src/                       ← OddsHarvester source
   │   ├── cli/
   │   ├── core/
   │   ├── storage/
   │   ├── utils/
   │   └── main.py
   ├── requirements.txt
   └── README.md
   ```

### Step 2: Create a GitHub Gist

1. Go to https://gist.github.com
2. Click **"+"** to create a new gist
3. **Filename:** `odds.json`
4. **Content:** Just put `{}` for now
5. Click **"Create secret gist"** (or public, doesn't matter)
6. **Copy the Gist ID** from the URL:
   ```
   https://gist.github.com/YOUR_USERNAME/abc123def456
                                         ^^^^^^^^^^^^
                                         This is your GIST_ID
   ```

### Step 3: Create a Personal Access Token

1. Go to https://github.com/settings/tokens?type=beta
2. Click **"Generate new token"** → **"Fine-grained token"**
3. Configure:
   - **Name:** `odds-harvester-gist`
   - **Expiration:** 90 days (or longer)
   - **Repository access:** "Only select repositories" → select your `odds-harvester` repo
   - **Permissions:**
     - **Repository permissions:** None needed
     - **Account permissions:** 
       - Gists: **Read and write**
4. Click **"Generate token"**
5. **Copy the token immediately!** (you won't see it again)

### Step 4: Add Secrets to Your Repo

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **"New repository secret"** and add:

   | Name | Value |
   |------|-------|
   | `GIST_TOKEN` | Your personal access token from Step 3 |
   | `GIST_ID` | The gist ID from Step 2 (e.g., `abc123def456`) |

### Step 5: Test the Workflow

1. Go to your repo → **Actions** tab
2. Click **"Scrape Soccer Odds"** workflow
3. Click **"Run workflow"** → **"Run workflow"**
4. Wait 5-10 minutes for it to complete
5. Check your Gist - it should now have odds data!

### Step 6: Get Your Gist Raw URL

Your WatchyScore app will fetch from:
```
https://gist.githubusercontent.com/YOUR_USERNAME/GIST_ID/raw/odds.json
```

For example:
```
https://gist.githubusercontent.com/jakekanu/abc123def456/raw/odds.json
```

### Step 7: Update WatchyScore

Add this environment variable to your Vercel project:
```
ODDS_HARVESTER_URL=https://gist.githubusercontent.com/YOUR_USERNAME/GIST_ID/raw/odds.json
```

---

## Customization

### Scrape More Leagues

Edit `.github/workflows/scrape-odds.yml` and add `--leagues`:

```yaml
- name: Scrape today's matches
  run: |
    python src/main.py scrape_upcoming \
      --sport football \
      --leagues england-premier-league,spain-laliga,germany-bundesliga,italy-serie-a,france-ligue-1,champions-league,europa-league \
      --markets 1x2 \
      --headless \
      --file_path data/today.json
```

### Available Leagues

See `src/utils/sport_league_constants.py` for the full list. Key ones:
- `england-premier-league`
- `england-championship`
- `spain-laliga`
- `germany-bundesliga`
- `italy-serie-a`
- `france-ligue-1`
- `champions-league`
- `europa-league`
- `usa-mls`
- `brazil-serie-a`
- `eredivisie`
- `liga-portugal`

### Change Scrape Frequency

Edit the cron schedule in `.github/workflows/scrape-odds.yml`:

```yaml
on:
  schedule:
    - cron: '0 */3 * * *'  # Every 3 hours
    # - cron: '0 */2 * * *'  # Every 2 hours
    # - cron: '0 */6 * * *'  # Every 6 hours
```

---

## Troubleshooting

### Workflow fails with timeout
- OddsPortal may be blocking. Try adding delays or using fewer leagues.

### Gist not updating
- Check that `GIST_TOKEN` has "Gists: Read and write" permission
- Check that `GIST_ID` is correct (just the ID, not the full URL)

### Empty odds.json
- Check the workflow logs for scraping errors
- Try running manually with `workflow_dispatch`

---

## Cost

**$0** - GitHub Actions free tier includes 2,000 minutes/month. 
This workflow uses ~5-10 minutes per run × 8 runs/day = ~40-80 minutes/day = ~1,200-2,400 minutes/month.

You're within the free tier! 🎉
