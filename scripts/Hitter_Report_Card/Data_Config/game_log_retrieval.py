import os

import requests
import pandas as pd
import boto3
from dotenv import load_dotenv

# Constants
MLB_SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2024-01-01&endDate=2024-12-31&gameType=R&fields=dates,date,games,gamePk,status,abstractGameState,teams,away,home,team,id,name,gameDate"
S3_BUCKET = "mlb_game_data"
S3_KEY = "mlb_game_schedule_2024.csv"

# Load environment variables
load_dotenv()

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT", 5432)
}

def fetch_and_store_mlb_schedule():
    """Fetches the 2024 MLB schedule and stores it in an S3 CSV file."""

    response = requests.get(MLB_SCHEDULE_URL)
    if response.status_code != 200:
        print(f"⚠ Error fetching schedule: {response.status_code}")
        return

    data = response.json()
    games_list = []

    for date_entry in data.get("dates", []):
        for game in date_entry.get("games", []):
            games_list.append({
                "game_id": game["gamePk"],
                "game_date": game["gameDate"].split("T")[0],  # YYYY-MM-DD format
                "home_team": game["teams"]["home"]["team"]["name"],
                "away_team": game["teams"]["away"]["team"]["name"]
            })

    # Convert to DataFrame
    df_games = pd.DataFrame(games_list)

    # Save locally
    csv_filename = "mlb_game_schedule_2024.csv"
    df_games.to_csv(csv_filename, index=False)
    print(f"CSV saved locally: {csv_filename}")

# Run the function to fetch and store the schedule
fetch_and_store_mlb_schedule()
