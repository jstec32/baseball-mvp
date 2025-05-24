import os
import boto3
import requests
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
from dotenv import load_dotenv
import psycopg2

load_dotenv()

# Postgres config (to upsert into pitcher_game_logs)
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432)),
}

# S3 config (optional CSV backup)
S3_BUCKET_NAME = "baseball-data-mvp"
S3_KEY           = "pitcher_game_logs/2025_pitcher_game_logs.csv"
s3 = boto3.client(
    "s3",
    aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
)

def fetch_game_pks_by_date(date_str):
    url    = "https://statsapi.mlb.com/api/v1/schedule"
    params = {"sportId": 1, "startDate": date_str, "endDate": date_str}
    resp   = requests.get(url, params=params)
    resp.raise_for_status()
    data   = resp.json()
    return [g["gamePk"] for d in data["dates"] for g in d["games"]]

def fetch_pitching_box(game_pk):
    url  = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
    resp = requests.get(url); resp.raise_for_status()
    data = resp.json()["teams"]

    rows = []
    for side in ("home","away"):
        team_block = data[side]
        for player_id, p in team_block["players"].items():
            stats = p.get("stats", {}).get("pitching", {})
            if not stats:
                continue
            rows.append({
                "game_date":         p["person"].get("gameDate"),  # might need to pass date in
                "game_pk":           game_pk,
                "pitcher_id":   p["person"]["id"],
                "outs_pitched":      stats.get("outs", 0),
                "earned_runs":       stats.get("earnedRuns", 0),
                "strikeouts":        stats.get("strikeOuts", 0),
                "walks":             stats.get("baseOnBalls", 0)
            })
    return pd.DataFrame(rows)

def load_existing_logs():
    try:
        obj = s3.get_object(Bucket=S3_BUCKET_NAME, Key=S3_KEY)
        return pd.read_csv(obj["Body"])
    except s3.exceptions.NoSuchKey:
        return pd.DataFrame()

def save_logs_to_s3(df):
    buf = StringIO()
    df.to_csv(buf, index=False)
    s3.put_object(Bucket=S3_BUCKET_NAME, Key=S3_KEY, Body=buf.getvalue())
    print("Saved pitcher_game_logs CSV to S3")

def upsert_db(df: pd.DataFrame):
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()
    sql = """
    INSERT INTO pitcher_game_logs
      (game_date, game_pk, pitcher_id, outs_pitched, earned_runs, strikeouts, walks)
    VALUES (%(game_date)s, %(game_pk)s, %(pitcher_id)s, %(outs_pitched)s, %(earned_runs)s, %(strikeouts)s, %(walks)s)
    ON CONFLICT (game_pk, pitcher_id) DO UPDATE SET
      outs_pitched = EXCLUDED.outs_pitched,
      earned_runs  = EXCLUDED.earned_runs,
      strikeouts   = EXCLUDED.strikeouts,
      walks        = EXCLUDED.walks;
    """
    for rec in df.to_dict(orient="records"):
        cur.execute(sql, rec)
    conn.commit()
    cur.close()
    conn.close()
    print(f"Upserted {len(df)} rows into pitcher_game_logs")

def pitcher_game_logs_intake(target_date: str):
    if target_date is None:
        target_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    pks = fetch_game_pks_by_date(target_date)
    all_new = []
    for pk in pks:
        df = fetch_pitching_box(pk)
        if not df.empty:
            df["game_date"] = target_date
            all_new.append(df)

    if not all_new:
        print("No pitching lines for", target_date)
        return

    new_df      = pd.concat(all_new, ignore_index=True)
    existing_df = load_existing_logs()
    full_df     = pd.concat([existing_df, new_df], ignore_index=True)
    full_df.drop_duplicates(subset=["game_pk","pitcher_id"], keep="last", inplace=True)

    # save to S3 backup
    save_logs_to_s3(full_df)
    # upsert into Postgres
    upsert_db(new_df)

from datetime import datetime, timedelta

def backfill_pitcher_game_logs(start_date: str, end_date: str):

    sd = datetime.strptime(start_date, "%Y-%m-%d")
    ed = datetime.strptime(end_date,   "%Y-%m-%d")
    cur = sd
    while cur <= ed:
        ds = cur.strftime("%Y-%m-%d")
        print(f"\n Backfilling pitcher logs for {ds}")
        try:
            pitcher_game_logs_intake(ds)
        except Exception as e:
            print(f"ERROR on {ds}: {e}")
        cur += timedelta(days=1)
    print(" Backfill complete.")


# At the top of the file, define your backfill window:
BACKFILL_START = "2025-05-22"  # Opening Day 2025
# You can also compute end dynamically:
BACKFILL_END   = "2025-05-22"

# … rest of imports & functions stay the same …

if __name__ == "__main__":
    # Always backfill the full range when you run this script
    print(f"🔄 Backfilling from {BACKFILL_START} to {BACKFILL_END}")
    backfill_pitcher_game_logs(BACKFILL_START, BACKFILL_END)

