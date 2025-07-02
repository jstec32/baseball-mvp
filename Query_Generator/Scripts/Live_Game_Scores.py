import requests
import psycopg2
import os
from datetime import datetime
from fastapi import Query
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# DB Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432))
}

def fetch_mlb_scores(date: datetime.date):
    formatted_date = date.strftime("%Y-%m-%d")
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={formatted_date}&hydrate=team,linescore"

    res = requests.get(url)
    res.raise_for_status()
    data = res.json()

    # Step 1: Get name → abbreviation mapping
    team_abbr_map = {}
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute("SELECT name, abbreviation_games FROM teams;")
            rows = cur.fetchall()
            team_abbr_map = {name: abbr for name, abbr in rows}
    finally:
        conn.close()

    # Step 2: Parse API results
    results = []
    for date_info in data.get("dates", []):
        for game in date_info.get("games", []):
            home_team = game["teams"]["home"]["team"]["name"]
            away_team = game["teams"]["away"]["team"]["name"]
            home_score = game["teams"]["home"].get("score", 0)
            away_score = game["teams"]["away"].get("score", 0)

            linescore = game.get("linescore", {})
            inning = linescore.get("currentInningOrdinal", "N/A")
            state = linescore.get("inningState", "")
            inning_display = f"{state} {inning}".strip() if inning != "N/A" else "Final"

            results.append({
                "home_team": home_team,
                "away_team": away_team,
                "home_abbr": team_abbr_map.get(home_team, home_team),
                "away_abbr": team_abbr_map.get(away_team, away_team),
                "home_score": home_score,
                "away_score": away_score,
                "inning": inning_display
            })

    return results
