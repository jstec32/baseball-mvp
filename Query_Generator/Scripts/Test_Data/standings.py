import os
import requests
import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432))
}

def fetch_wild_card_standings():
    url = "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2025&standingsTypes=wildCard"
    res = requests.get(url)
    res.raise_for_status()
    data = res.json()

    rows = []
    for record in data["records"]:
        league_id = record.get("league", {}).get("id")
        league = "AL" if league_id == 103 else "NL"

        for team in record["teamRecords"]:
            name = team["team"]["name"]
            wins = team["wins"]
            losses = team["losses"]
            pct = team["winningPercentage"]
            gb = team["wildCardGamesBack"]
            streak = team["streak"]["streakCode"]
            rank = team["wildCardRank"]

            rows.append({
                "league": league,
                "rank": int(rank),
                "team": name,
                "wins": wins,
                "losses": losses,
                "pct": pct,
                "gb": gb,
                "streak": streak
            })

    df = pd.DataFrame(rows).sort_values(["league", "rank"])
    return df

# Run it
df_wildcard = fetch_wild_card_standings()
print(df_wildcard.head(20))




