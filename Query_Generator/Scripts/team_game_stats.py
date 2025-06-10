import os
import boto3
import pandas as pd
import requests
from io import BytesIO, StringIO
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

S3_BUCKET = "baseball-data-mvp"
CSV_KEY = "mlb_game_data/team_game_stats_2025.csv"
GAME_DATA_KEY = "mlb_game_data/mlb_game_data_2025.csv"

s3 = boto3.client(
    "s3",
    aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name           = os.getenv("AWS_REGION", "us-east-1")
)

def fetch_yesterday_team_stats_and_append_to_s3():
    # Determine yesterday’s date
    target_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"Processing team stats for {target_date}...")

    # Load game data and filter by date
    obj = s3.get_object(Bucket=S3_BUCKET, Key=GAME_DATA_KEY)
    df = pd.read_csv(BytesIO(obj["Body"].read()), parse_dates=["game_date"])
    game_info = df[df["game_date"].dt.strftime("%Y-%m-%d") == target_date][["game_id", "game_date"]].drop_duplicates()

    if game_info.empty:
        print(f"No games found on {target_date}")
        return

    new_records = []

    for _, row in game_info.iterrows():
        game_pk = row["game_id"]
        game_date = row["game_date"].strftime("%Y-%m-%d")

        try:
            url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
            resp = requests.get(url)
            resp.raise_for_status()
            teams = resp.json()["teams"]

            for side in ("home", "away"):
                team_data = teams[side]
                team_name = team_data["team"]["name"]
                stats = team_data.get("teamStats", {})

                row_data = {
                    "game_pk": game_pk,
                    "game_date": game_date,
                    "team_name": team_name,
                    "is_home_team": side == "home"
                }

                for category in ("batting", "pitching", "fielding"):
                    for k, v in stats.get(category, {}).items():
                        if isinstance(v, (int, float)):
                            col = f"{category}_{k}"
                            row_data[col] = v

                new_records.append(row_data)

        except Exception as e:
            print(f"Error fetching game {game_pk}: {e}")

    if not new_records:
        print("No team stats collected.")
        return

    df_new = pd.DataFrame(new_records)

    # Load existing CSV from S3 (if exists)
    try:
        obj = s3.get_object(Bucket=S3_BUCKET, Key=CSV_KEY)
        df_existing = pd.read_csv(BytesIO(obj["Body"].read()))
        df_full = pd.concat([df_existing, df_new], ignore_index=True)
        print("Appended to existing CSV.")
    except s3.exceptions.NoSuchKey:
        df_full = df_new
        print("Creating new team_game_stats_2025.csv")

    # Save updated CSV back to S3
    buffer = StringIO()
    df_full.to_csv(buffer, index=False)
    s3.put_object(Bucket=S3_BUCKET, Key=CSV_KEY, Body=buffer.getvalue())
    print(f"Saved updated CSV to s3://{S3_BUCKET}/{CSV_KEY}")




