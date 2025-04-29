import boto3
import requests
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv()

# S3 Config
S3_BUCKET_NAME = "baseball-data-mvp"
S3_KEY = "mlb_game_data/box_scores_2025.csv"


s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)


def fetch_game_pks_by_date(date_str):
    url = "https://statsapi.mlb.com/api/v1/schedule"
    params = {"sportId": 1, "startDate": date_str, "endDate": date_str}
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"Failed to fetch game schedule for {date_str}")
        return []
    data = response.json()
    return [game["gamePk"] for date in data["dates"] for game in date["games"]]


def fetch_box_score_raw(game_pk):
    url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch box score for game {game_pk}")
        return None

    data = response.json()
    teams = ["home", "away"]
    rows = []

    for team in teams:
        team_data = data["teams"][team]
        team_name = team_data["team"]["name"]

        for player_id, pdata in team_data["players"].items():
            row = {
                "game_pk": game_pk,
                "team": team_name,
                "player_id": player_id,
                "name": pdata["person"]["fullName"]
            }

            stats = pdata.get("stats", {}).get("batting", {})
            keys = [
                "atBats", "runs", "hits", "doubles", "triples", "homeRuns",
                "rbi", "baseOnBalls", "strikeOuts", "sacFlies", "sacBunts",
                "stolenBases", "caughtStealing", "leftOnBase", "groundIntoDoublePlay", "hitByPitch"
            ]
            for k in keys:
                row[k] = stats.get(k, 0)

            rows.append(row)

    col_order = ["game_pk", "team", "player_id", "name", "atBats", "runs", "hits",
                 "doubles", "triples", "homeRuns", "rbi", "baseOnBalls", "strikeOuts",
                 "sacFlies", "sacBunts", "stolenBases", "caughtStealing", "leftOnBase",
                 "groundIntoDoublePlay", "hitByPitch"]

    return pd.DataFrame(rows, columns=col_order)


def load_existing_box_scores():
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=S3_KEY)
        df = pd.read_csv(response["Body"])
        print("Loaded existing box_scores_2025.csv from S3")
        return df
    except s3_client.exceptions.NoSuchKey:
        print("No existing box_scores_2025.csv found — creating new file.")
        return pd.DataFrame()


def save_to_s3(df):
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=S3_KEY, Body=csv_buffer.getvalue())
    print(f"Uploaded updated box_scores_2025.csv to S3")


def boxscore_intake(target_date=None):
    if target_date is None:
        target_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")


    game_pks = fetch_game_pks_by_date(target_date)

    if not game_pks:
        print("No games found for yesterday.")
        return


    existing_df = load_existing_box_scores()


    new_rows = []
    for game_pk in game_pks:
        df = fetch_box_score_raw(game_pk)
        if df is not None:
            new_rows.append(df)

    if not new_rows:
        print("No new box score data retrieved.")
        return

    new_data = pd.concat(new_rows, ignore_index=True)
    new_data["game_date"] = target_date


    full_df = pd.concat([existing_df, new_data], ignore_index=True)
    full_df.drop_duplicates(subset=["game_pk", "player_id"], keep="last", inplace=True)
    save_to_s3(full_df)
    print(f"Box Scores Intake Complete for {target_date}")

if __name__ == "__main__":
    boxscore_intake()
