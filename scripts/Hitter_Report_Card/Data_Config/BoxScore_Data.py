import boto3
import requests
import pandas as pd
import json
from io import StringIO
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables (for S3 credentials)
load_dotenv()

# S3 Configuration - Update these with your actual bucket & path
S3_BUCKET_NAME = "baseball-data-mvp"  # Replace with your bucket name
S3_FOLDER = "mlb_game_data/"

# S3 client (make sure your AWS credentials are configured properly)
s3_client = boto3.client("s3")

def fetch_all_game_pks_2024():
    url = "https://statsapi.mlb.com/api/v1/schedule"
    params = {
        "sportId": 1,
        "startDate": "2024-03-28",
        "endDate": "2024-10-01"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    game_pks = []
    for date in data['dates']:
        for game in date['games']:
            game_pks.append(game['gamePk'])

    print(f" Fetched {len(game_pks)} games for 2024")
    return game_pks


def fetch_box_score_raw(game_pk):

    url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
    response = requests.get(url)

    if response.status_code != 200:
        print(f" Failed to fetch box score for game {game_pk}, status: {response.status_code}")
        return None

    data = response.json()

    teams = ["home", "away"]
    all_rows = []

    for team in teams:
        team_data = data["teams"][team]
        team_name = team_data["team"]["name"]

        for player_id, player_data in team_data["players"].items():
            row = {
                "game_pk": game_pk,
                "team": team_name,
                "player_id": player_id,
                "name": player_data["person"]["fullName"],
            }

            # Pull batting stats if they exist
            batting_stats = player_data.get("stats", {}).get("batting", {})

            # Directly pull only the relevant stats
            important_stats = [
                "atBats", "runs", "hits", "doubles", "triples", "homeRuns",
                "rbi", "baseOnBalls", "strikeOuts", "sacFlies", "sacBunts",
                "stolenBases", "caughtStealing", "leftOnBase", "groundIntoDoublePlay","hitByPitch"
            ]

            for stat in important_stats:
                row[stat] = batting_stats.get(stat, 0)  # Default to 0 if missing

            all_rows.append(row)

    # Create DataFrame with enforced column order
    columns_order = [
        "game_pk", "team", "player_id", "name", "atBats", "runs", "hits",
        "doubles", "triples", "homeRuns", "rbi", "baseOnBalls", "strikeOuts",
        "sacFlies", "sacBunts", "stolenBases", "caughtStealing", "leftOnBase",
        "groundIntoDoublePlay","hitByPitch"
    ]

    df = pd.DataFrame(all_rows, columns=columns_order)

    return df



def upload_box_score_to_s3(file_path, year=2024):
    bucket_name = os.getenv("S3_BUCKET_NAME")
    s3_key = f"mlb_game_data/box_scores_{year}.csv"

    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    try:
        s3.upload_file(file_path, bucket_name, s3_key)
        print(f" Uploaded box scores to S3: s3://{bucket_name}/{s3_key}")
    except Exception as e:
        print(f" Error uploading box scores: {e}")



def main():
    game_pks = fetch_all_game_pks_2024()

    all_box_scores = []
    for game_pk in game_pks:
        df = fetch_box_score_raw(game_pk)
        if df is not None and not df.empty:
            all_box_scores.append(df)

    full_box_score_df = pd.concat(all_box_scores, ignore_index=True)

    # Save locally
    file_path = f"2024_full_box_scores.csv"
    full_box_score_df.to_csv(file_path, index=False)

    # Upload directly to S3 — no DataFrame check needed
    upload_box_score_to_s3(file_path, 2024)

if __name__ == "__main__":
    main()


