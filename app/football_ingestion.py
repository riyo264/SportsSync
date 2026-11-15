import os
import httpx
import time
from datetime import datetime, timedelta

FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")
HEADERS = {
    "x-apisports-key": FOOTBALL_API_KEY
}

LEAGUE_IDS = {
    "premier_league": 39,
    "laliga": 140,
    "ucl": 2,
    "isl": 323
}

# --- IN-MEMORY TTL CACHE ---
league_cache = {}
CACHE_TTL = 300  # 5 minutes

def get_current_season() -> int:
    """European & ISL seasons start around Aug/Sep, so Nov 2026 belongs to the 2026 season."""
    now = datetime.utcnow()
    return now.year if now.month >= 7 else now.year - 1

async def fetch_league_matches(league_key: str, league_id: int):
    """Fetches live matches. If NONE are live, falls back to the 2 most recent completed matches."""
    if not FOOTBALL_API_KEY:
        print("[ERROR] FOOTBALL_API_KEY is missing from environment variables!")
        return []

    base_url = "https://v3.football.api-sports.io/fixtures"

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Check for LIVE matches first
        live_res = await client.get(
            base_url,
            headers=HEADERS,
            params={"league": league_id, "live": "all"}
        )
        live_data = live_res.json()

        if live_data.get("errors"):
            print(f"[API-FOOTBALL ERROR - LIVE {league_key}]: {live_data['errors']}")

        matches = live_data.get("response", [])

        # 2. STRICT FALLBACK: Only fetch completed fixtures if there are ZERO live matches
        if not matches:
            for season in [2026, 2025, 2024, 2023]:
                recent_res = await client.get(
                    base_url,
                    headers=HEADERS,
                    params={
                        "league": league_id,
                        "season": season,
                        "status": "FT-AET-PEN"
                    }
                )
                recent_data = recent_res.json()

                if recent_data.get("errors"):
                    print(f"[API-FOOTBALL ERROR - RECENT {league_key} (Season {season})]: {recent_data['errors']}")
                    continue 

                all_finished = recent_data.get("response", [])
                if all_finished:
                    # Sort chronologically (newest first) and take the 2 most recent matches
                    all_finished.sort(key=lambda x: x["fixture"]["timestamp"], reverse=True)
                    matches = all_finished[:2]
                    break 

        formatted_matches = []
        for m in matches:
            fixture = m["fixture"]
            teams = m["teams"]
            goals = m["goals"]

            short_status = fixture["status"]["short"]
            is_live = short_status in ["1H", "2H", "HT", "ET", "P", "LIVE"]

            if is_live:
                elapsed = fixture["status"].get("elapsed")
                status_text = f"{elapsed}'" if elapsed else short_status
            else:
                date_obj = datetime.fromisoformat(fixture["date"])
                status_text = f"{short_status} • {date_obj.strftime('%b %d')}"

            formatted_matches.append({
                "id": f"football_{league_key}_{fixture['id']}",
                "home": teams["home"]["name"],
                "away": teams["away"]["name"],
                "homeScore": goals["home"] if goals["home"] is not None else 0,
                "awayScore": goals["away"] if goals["away"] is not None else 0,
                "isLive": is_live,
                "statusText": status_text,
                "fixture_id": fixture["id"]
            })

        return formatted_matches

async def get_cached_league(league_key: str):
    """Checks memory cache before hitting API-Football. Never caches empty responses."""
    now = time.time()

    if league_key in league_cache:
        if now - league_cache[league_key]["timestamp"] < CACHE_TTL:
            print(f"[CACHE HIT] Returning {league_key} from memory")
            return league_cache[league_key]["data"]

    print(f"[CACHE MISS] Fetching {league_key} from API-Football...")
    league_id = LEAGUE_IDS.get(league_key)
    if not league_id:
        return []

    fresh_data = await fetch_league_matches(league_key, league_id)

    if fresh_data:
        league_cache[league_key] = {
            "data": fresh_data,
            "timestamp": now
        }

    return fresh_data

async def get_match_context(fixture_id: str):
    """Fetches live match events (goals, cards) to feed into the Gemini LLM."""
    if not FOOTBALL_API_KEY:
        return "Football API Key missing."

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(
            "https://v3.football.api-sports.io/fixtures/events",
            headers=HEADERS,
            params={"fixture": fixture_id}
        )
        data = res.json()
        events = data.get("response", [])

        if not events:
            return "No major events (goals, cards, or substitutions) have occurred yet, or data is unavailable."

        context_lines = []
        for e in events:
            time_elapsed = e["time"]["elapsed"]
            team = e["team"]["name"]
            player = e["player"]["name"]
            event_type = e["type"]  # e.g., 'Goal', 'Card', 'subst'
            detail = e["detail"]    # e.g., 'Normal Goal', 'Yellow Card'
            
            context_lines.append(f"{time_elapsed}' - {team}: {player} ({event_type} - {detail})")

        return "\n".join(context_lines)