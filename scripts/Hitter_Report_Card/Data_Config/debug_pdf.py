import os
from io import StringIO

import boto3
import pandas as pd


def load_player_opponent(game_id,team_name):
    S3_BUCKET = "scouting-reports-bucket"
    S3_FOLDER = "mlb_game_data"
    S3_KEY = "mlb_game_schedule_2024.csv"
    S3_full_key = f"{S3_FOLDER}/{S3_KEY}"
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=S3_full_key)
        df_games = pd.read_csv(StringIO(response["Body"].read().decode("utf-8")))
        print(df_games.head())
        # Find the row with the matching game_id
        game_row = df_games[df_games["game_id"] == game_id]
        if game_row.empty:
            print(f" No game found for game_id {game_id}")
            return "Opponent Unknown"

        # Determine opponent based on player's team
        row = game_row.iloc[0]
        if row["home_team"] == team_name:
            return row["away_team"]
        else:
            return row["home_team"]

    except Exception as e:
        print(f"Error fetching opponent from S3: {e}")
        return "Opponent Unknown"

opponent = load_player_opponent('745201', 'Seattle Mariners')