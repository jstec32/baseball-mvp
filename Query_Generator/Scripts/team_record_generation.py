#!/usr/bin/env python3
import os
import pandas as pd
from io import BytesIO
import psycopg2
import boto3
from dotenv import load_dotenv

load_dotenv()


# 1) POSTGRES CONFIGURATION (from your .env)
DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port":     int(os.getenv("DB_PORT", 5432)),
}


#S3 CONFIGURATION
S3_BUCKET    = "baseball-data-mvp"
S3_KEY_GAMES = "mlb_game_data/mlb_game_data_2025.csv"

s3_client = boto3.client(
    "s3",
    aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name           = os.getenv("AWS_REGION", "us-east-1")
)


def fetch_mlb_game_data() -> pd.DataFrame:

    print(f"► Downloading '{S3_KEY_GAMES}' from bucket '{S3_BUCKET}' …")
    obj = s3_client.get_object(Bucket=S3_BUCKET, Key=S3_KEY_GAMES)
    raw = obj["Body"].read()
    df  = pd.read_csv(BytesIO(raw))

    # Normalize game_date column
    if "game_date" in df.columns:
        df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce", infer_datetime_format=True)

    return df


def compute_team_records(df_games: pd.DataFrame) -> pd.DataFrame:

    # 1) Keep only full‐season games (i.e. series_description != 'Spring Training')
    df_rs = df_games[ df_games["series_description"].str.lower() != "spring training" ].copy()

    # 2) Keep only 2025 calendar‐year (in case there are pre‐ or post‐season entries)
    df_rs = df_rs[ df_rs["game_date"].dt.year == 2025 ].copy()

    # 3) Drop rows missing score or team
    df_rs = df_rs.dropna(subset=["home_team", "away_team", "home_score", "away_score"])

    # 4) Convert scores to integers
    df_rs["home_score"] = df_rs["home_score"].astype(int)
    df_rs["away_score"] = df_rs["away_score"].astype(int)

    # 5) separate home and away games
    home = df_rs[["home_team", "home_score", "away_score", "game_id"]].copy()
    home.columns = ["team", "for_score", "against_score", "game_id"]

    away = df_rs[["away_team", "away_score", "home_score", "game_id"]].copy()
    away.columns = ["team", "for_score", "against_score", "game_id"]

    df_all = pd.concat([home, away], ignore_index=True)

    df_all["win"]  = (df_all["for_score"] > df_all["against_score"]).astype(int)
    df_all["loss"] = (df_all["for_score"] < df_all["against_score"]).astype(int)
    rec = (
        df_all
        .groupby("team", observed=True)
        .agg(
            games_played = ("game_id", "nunique"),
            wins         = ("win", "sum"),
            losses       = ("loss", "sum"),
        )
        .reset_index()
    )

    return rec

def upsert_team_records(df_records: pd.DataFrame) -> None:

    print("Connecting to Postgres…")
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()

    upsert_sql = """
    INSERT INTO teams (name, wins, losses, games_played)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (name) DO UPDATE
      SET wins         = EXCLUDED.wins,
          losses       = EXCLUDED.losses,
          games_played = EXCLUDED.games_played;
    """
    for _, row in df_records.iterrows():
        cur.execute(
            upsert_sql,
            (
                row["team"],
                int(row["wins"]),
                int(row["losses"]),
                int(row["games_played"]),
            )
        )

    conn.commit()
    cur.close()
    conn.close()
    print("► Upsert into teams table complete.")

def update_team_records():
    try:
        df_games = fetch_mlb_game_data()
        if df_games.empty:
            print("No game data returned. Skipping team record update.")
            return
        df_records = compute_team_records(df_games)
        print(df_records.head(), "\n")
        upsert_team_records(df_records)
        print("Team records updated.")
    except Exception as e:
        print(f"Error updating team records: {e}")


if __name__ == "__main__":

    df_games = fetch_mlb_game_data()
    df_records = compute_team_records(df_games)
    print("Computed team records (first few rows):")
    print(df_records.head(), "\n")
    upsert_team_records(df_records)

    print("All done.")
