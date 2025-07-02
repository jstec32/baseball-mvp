import os
import requests
import psycopg2
import pandas as pd
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# DB config
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432))
}

# Fetch MLB API standings data
url = "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2025&standingsTypes=regularSeason"
res = requests.get(url)
res.raise_for_status()
data = res.json()

# Parse team records from all divisions
records = []
for league in data["records"]:
    for team in league["teamRecords"]:
        team_name = team["team"]["name"]
        league_record = team["leagueRecord"]
        records.append({
            "team": team_name,
            "wins": league_record["wins"],
            "losses": league_record["losses"],
            "pct": league_record["pct"],
            "gb": team["gamesBack"],
            "streak": team["streak"]["streakCode"]
        })

standings_df = pd.DataFrame(records)

# Get division info from database
try:
    conn = psycopg2.connect(**DB_CONFIG)
    query = "SELECT name, division FROM teams;"
    teams_df = pd.read_sql(query, conn)
    conn.close()
except Exception as e:
    print("Database error:", e)
    raise

# Merge API data with division info
merged_df = pd.merge(standings_df, teams_df, left_on="team", right_on="name", how="left")
final_df = merged_df[["division", "team", "wins", "losses", "pct", "gb", "streak"]]
final_df = final_df.sort_values(["division", "wins"], ascending=[True, False])

print(final_df.head(20))


