/**
 * Odds Harvester - Fetches betting odds from football-data.co.uk Gist
 * 
 * This module fetches pre-match odds for upcoming fixtures.
 * Data source: football-data.co.uk (via GitHub Gist)
 * 
 * Coverage: ~20 European leagues including:
 * - Premier League, Championship, League 1, League 2
 * - Bundesliga, 2. Bundesliga
 * - Serie A, Serie B
 * - La Liga, Segunda
 * - Ligue 1, Ligue 2
 * - Eredivisie, Primeira Liga, Super Lig, etc.
 */

// Default Gist URL - can be overridden via environment variable
const DEFAULT_ODDS_URL = 'https://gist.githubusercontent.com/jeisner23/5d2a07b5e6e75c030679cdbeb671e931/raw/odds.json';

/**
 * Fetches odds data from the Gist
 */
async function fetchOddsFromGist() {
    const url = process.env.ODDS_HARVESTER_URL || DEFAULT_ODDS_URL;
    
    try {
        const response = await fetch(url, {
            headers: {
                'Accept': 'application/json',
                'Cache-Control': 'no-cache'
            }
        });
        
        if (!response.ok) {
            console.error(`[odds-harvester] Failed to fetch odds: ${response.status}`);
            return null;
        }
        
        const data = await response.json();
        
        // Log stats
        const matchCount = data.matches?.length || 0;
        const lastUpdated = data.last_updated || 'unknown';
        console.log(`[odds-harvester] Loaded ${matchCount} matches, last updated: ${lastUpdated}`);
        
        return data;
        
    } catch (error) {
        console.error(`[odds-harvester] Error fetching odds:`, error.message);
        return null;
    }
}

/**
 * Normalize team names for matching
 * Handles common variations and abbreviations
 */
function normalizeTeamName(name) {
    if (!name) return '';
    
    return name
        .toLowerCase()
        .trim()
        // Remove common suffixes
        .replace(/\s*(fc|cf|sc|afc|ac|as|ss|us|cd|ud|rc|sd|fk|sk|bk|if|bf|nk|rsc|kv|sv|tsv|vfb|vfl|1\.)$/gi, '')
        // Remove special characters
        .replace(/[''`´]/g, '')
        .replace(/[-_]/g, ' ')
        // Normalize spaces
        .replace(/\s+/g, ' ')
        .trim();
}

/**
 * Calculate similarity between two team names
 * Returns a score from 0 to 1
 */
function teamNameSimilarity(name1, name2) {
    const n1 = normalizeTeamName(name1);
    const n2 = normalizeTeamName(name2);
    
    if (n1 === n2) return 1.0;
    
    // Check if one contains the other
    if (n1.includes(n2) || n2.includes(n1)) return 0.9;
    
    // Check word overlap
    const words1 = new Set(n1.split(' '));
    const words2 = new Set(n2.split(' '));
    const intersection = [...words1].filter(w => words2.has(w));
    const union = new Set([...words1, ...words2]);
    const jaccard = intersection.length / union.size;
    
    return jaccard;
}

/**
 * Find odds for a specific fixture
 * 
 * @param {Object} oddsData - The full odds data from Gist
 * @param {string} homeTeam - Home team name
 * @param {string} awayTeam - Away team name
 * @param {Date|string} matchDate - Match date (optional, for disambiguation)
 * @returns {Object|null} - Odds object or null if not found
 */
function findOddsForFixture(oddsData, homeTeam, awayTeam, matchDate = null) {
    if (!oddsData?.matches || !homeTeam || !awayTeam) {
        return null;
    }
    
    let bestMatch = null;
    let bestScore = 0;
    
    for (const match of oddsData.matches) {
        const homeScore = teamNameSimilarity(homeTeam, match.home_team);
        const awayScore = teamNameSimilarity(awayTeam, match.away_team);
        const combinedScore = (homeScore + awayScore) / 2;
        
        // Require minimum match quality
        if (combinedScore > 0.7 && combinedScore > bestScore) {
            // If match date provided, verify it's close
            if (matchDate) {
                const fixtureDate = new Date(match.commence_time);
                const targetDate = new Date(matchDate);
                const daysDiff = Math.abs((fixtureDate - targetDate) / (1000 * 60 * 60 * 24));
                
                // Skip if dates are more than 2 days apart
                if (daysDiff > 2) continue;
            }
            
            bestScore = combinedScore;
            bestMatch = match;
        }
    }
    
    if (!bestMatch) {
        return null;
    }
    
    // Transform to the format scoring-engine expects
    return {
        home: bestMatch.markets?.h2h?.home || null,
        draw: bestMatch.markets?.h2h?.draw || null,
        away: bestMatch.markets?.h2h?.away || null,
        over_2_5: bestMatch.markets?.totals?.over || null,
        under_2_5: bestMatch.markets?.totals?.under || null,
        source: oddsData.source || 'football-data.co.uk',
        last_updated: oddsData.last_updated
    };
}

/**
 * Main function to get odds for a fixture
 * This is the primary entry point used by fixtures-scored.js
 * 
 * @param {string} homeTeam - Home team name
 * @param {string} awayTeam - Away team name  
 * @param {Date|string} matchDate - Match date
 * @returns {Object|null} - Odds object with home/draw/away or null
 */
async function getOddsForFixture(homeTeam, awayTeam, matchDate = null) {
    // Fetch odds data (could add caching here)
    const oddsData = await fetchOddsFromGist();
    
    if (!oddsData) {
        return null;
    }
    
    return findOddsForFixture(oddsData, homeTeam, awayTeam, matchDate);
}

/**
 * Batch lookup for multiple fixtures
 * More efficient than individual lookups
 * 
 * @param {Array} fixtures - Array of {homeTeam, awayTeam, date} objects
 * @returns {Map} - Map of "homeTeam vs awayTeam" -> odds
 */
async function getOddsForFixtures(fixtures) {
    const oddsData = await fetchOddsFromGist();
    
    if (!oddsData) {
        return new Map();
    }
    
    const results = new Map();
    
    for (const fixture of fixtures) {
        const key = `${fixture.homeTeam} vs ${fixture.awayTeam}`;
        const odds = findOddsForFixture(
            oddsData, 
            fixture.homeTeam, 
            fixture.awayTeam, 
            fixture.date
        );
        if (odds) {
            results.set(key, odds);
        }
    }
    
    console.log(`[odds-harvester] Found odds for ${results.size}/${fixtures.length} fixtures`);
    
    return results;
}

/**
 * Get all available odds (for debugging/display)
 */
async function getAllOdds() {
    return await fetchOddsFromGist();
}

// Export for use in other modules
module.exports = {
    getOddsForFixture,
    getOddsForFixtures,
    getAllOdds,
    findOddsForFixture,
    normalizeTeamName,
    teamNameSimilarity
};

// Also export for ES modules
if (typeof exports !== 'undefined') {
    exports.getOddsForFixture = getOddsForFixture;
    exports.getOddsForFixtures = getOddsForFixtures;
    exports.getAllOdds = getAllOdds;
}
