import requests
import pandas as pd
import boto3
import os
from io import StringIO
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

# S3 Config
S3_BUCKET_NAME = "baseball-data-mvp"
S3_KEY = "mlb_game_data/mlb_game_data_2025.csv"

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)


def fetch_game_logs_for_date(date_str):
    url = f"http://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&startDate={date_str}&endDate={date_str}"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Failed to fetch MLB games for {date_str}")
        return None

    data = response.json()
    games_list = []

    for date_info in data.get("dates", []):
        for game in date_info.get("games", []):
            games_list.append({
                "game_id": game.get("gamePk"),
                "game_date": game.get("gameDate"),
                "venue": game.get("venue", {}).get("name", "Unknown Venue"),
                "home_team_id": game.get("teams", {}).get("home", {}).get("team", {}).get("id"),
                "home_team": game.get("teams", {}).get("home", {}).get("team", {}).get("name"),
                "home_score": game.get("teams", {}).get("home", {}).get("score"),
                "away_team_id": game.get("teams", {}).get("away", {}).get("team", {}).get("id"),
                "away_team": game.get("teams", {}).get("away", {}).get("team", {}).get("name"),
                "away_score": game.get("teams", {}).get("away", {}).get("score"),
                "series_description": game.get("seriesDescription", "Unknown Series"),
            })

    return pd.DataFrame(games_list)


def load_existing_game_log():
    try:
        response = s3.get_object(Bucket=S3_BUCKET_NAME, Key=S3_KEY)
        return pd.read_csv(response["Body"])
    except s3.exceptions.NoSuchKey:
        print("No existing game log found, creating new.")
        return pd.DataFrame()


def upload_updated_game_log(df):
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    s3.put_object(Bucket=S3_BUCKET_NAME, Key=S3_KEY, Body=csv_buffer.getvalue())
    print(f"Uploaded updated game log to S3: {S3_KEY}")

#create and upload game log
def game_log_generation(target_date=None):
    if target_date is None:
        target_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")


    new_df = fetch_game_logs_for_date(target_date)
    if new_df is None or new_df.empty:
        print("No new game data found.")
        return


    existing_df = load_existing_game_log()
    full_df = pd.concat([existing_df, new_df], ignore_index=True)
    full_df.drop_duplicates(subset=["game_id"], keep="last", inplace=True)
    upload_updated_game_log(full_df)
    print(f"Game logs updated successfully for {target_date}.")

if __name__ == "__main__":
    game_log_generation()
