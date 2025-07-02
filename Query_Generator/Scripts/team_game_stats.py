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
    target_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"Processing team stats for {target_date}...")

    obj = s3.get_object(Bucket=S3_BUCKET, Key=GAME_DATA_KEY)
    df = pd.read_csv(BytesIO(obj["Body"].read()), parse_dates=["game_date"])
    game_info = df[df["game_date"].dt.strftime("%Y-%m-%d") == target_date][["game_id", "game_date"]].drop_duplicates()

    if game_info.empty:
        print(f"No games found on {target_date}")
        return

    new_records = []
    run_cols = [f"runs_inning_{i}" for i in range(1, 10)]

    for _, row in game_info.iterrows():
        game_pk = row["game_id"]
        game_date = row["game_date"].strftime("%Y-%m-%d")

        try:
            box = requests.get(f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore").json()
            line = requests.get(f"https://statsapi.mlb.com/api/v1/game/{game_pk}/linescore").json()
            teams = box["teams"]

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
                            row_data[f"{category}_{k}"] = v

                # Pull inning-level runs from linescore["innings"]
                innings = line.get("innings", [])
                for i in range(9):
                    inning_val = innings[i].get(side, {}).get("runs") if i < len(innings) else 0
                    row_data[f"runs_inning_{i + 1}"] = inning_val if inning_val is not None else 0

                team_summary = line.get("teams", {}).get(side, {})
                row_data["team_total_runs"] = team_summary.get("runs")
                row_data["team_total_hits"] = team_summary.get("hits")
                row_data["team_total_errors"] = team_summary.get("errors")

                new_records.append(row_data)

        except Exception as e:
            print(f"Error fetching game {game_pk}: {e}")

    if not new_records:
        print("No team stats collected.")
        return

    df_new = pd.DataFrame(new_records)

    # Load existing CSV from S3
    try:
        obj = s3.get_object(Bucket=S3_BUCKET, Key=CSV_KEY)
        df_existing = pd.read_csv(BytesIO(obj["Body"].read()))
        df_full = pd.concat([df_existing, df_new], ignore_index=True)
        print("Appended to existing CSV.")
    except s3.exceptions.NoSuchKey:
        df_full = df_new
        print("Creating new team_game_stats_2025.csv")

    # Sort and write to S3
    df_full = df_full.sort_values(by=["game_date", "game_pk"]).reset_index(drop=True)
    buffer = StringIO()
    df_full.to_csv(buffer, index=False)
    s3.put_object(Bucket=S3_BUCKET, Key=CSV_KEY, Body=buffer.getvalue())
    print(f"Saved updated and sorted CSV to s3://{S3_BUCKET}/{CSV_KEY}")






