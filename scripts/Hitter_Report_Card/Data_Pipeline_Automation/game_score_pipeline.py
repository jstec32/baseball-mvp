import os
import boto3
import psycopg2
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = "baseball-data-mvp"

BOX_SCORES_KEY = "mlb_game_data/box_scores_2025.csv"
MERGED_KEY = "mlb_game_data/merged_pitch_box_scores_2025.csv"

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT", 5432)
}


def load_s3_csv(key):
    s3 = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    try:
        response = s3.get_object(Bucket=AWS_BUCKET_NAME, Key=key)
        return pd.read_csv(response["Body"])
    except s3.exceptions.NoSuchKey:
        print(f"S3 file {key} not found. Creating new.")
        return pd.DataFrame()


def upload_s3_csv(df, key):
    s3 = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    csv_buf = StringIO()
    df.to_csv(csv_buf, index=False)
    s3.put_object(Bucket=AWS_BUCKET_NAME, Key=key, Body=csv_buf.getvalue())
    print(f"Uploaded {key} to S3.")


def load_pitch_data_for_yesterday(target_date=None):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        if target_date is None:
            target_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        query = f"""
        WITH at_bat_max_hits AS (
            SELECT
                game_id,
                batter_id,
                "group",
                MAX(launch_speed) AS max_launch_speed,
                MAX(launch_angle) AS max_launch_angle
            FROM pitch_data
            WHERE description = 'hit_into_play' AND game_date = '{target_date}'
            GROUP BY game_id, batter_id, "group"
        ),
        barrel_hits AS (
            SELECT
                game_id,
                batter_id,
                COUNT(*) AS barrel_count
            FROM at_bat_max_hits
            WHERE 
                (max_launch_speed >= 98 AND max_launch_angle BETWEEN 8 AND 32) OR
                (max_launch_speed >= 99 AND max_launch_angle BETWEEN 9 AND 33) OR
                (max_launch_speed >= 100 AND max_launch_angle BETWEEN 10 AND 34) OR
                (max_launch_speed >= 101 AND max_launch_angle BETWEEN 11 AND 35) OR
                (max_launch_speed >= 102 AND max_launch_angle BETWEEN 12 AND 36) OR
                (max_launch_speed >= 103 AND max_launch_angle BETWEEN 13 AND 37) OR
                (max_launch_speed >= 104 AND max_launch_angle BETWEEN 14 AND 38) OR
                (max_launch_speed >= 105 AND max_launch_angle BETWEEN 15 AND 39) OR
                (max_launch_speed >= 106 AND max_launch_angle BETWEEN 16 AND 40) OR
                (max_launch_speed >= 107 AND max_launch_angle BETWEEN 17 AND 41) OR
                (max_launch_speed >= 108 AND max_launch_angle BETWEEN 18 AND 42) OR
                (max_launch_speed >= 109 AND max_launch_angle BETWEEN 19 AND 43) OR
                (max_launch_speed >= 110 AND max_launch_angle BETWEEN 20 AND 44) OR
                (max_launch_speed >= 111 AND max_launch_angle BETWEEN 21 AND 45) OR
                (max_launch_speed >= 112 AND max_launch_angle BETWEEN 22 AND 46) OR
                (max_launch_speed >= 113 AND max_launch_angle BETWEEN 23 AND 47) OR
                (max_launch_speed >= 114 AND max_launch_angle BETWEEN 24 AND 48) OR
                (max_launch_speed >= 115 AND max_launch_angle BETWEEN 25 AND 49) OR
                (max_launch_speed >= 116 AND max_launch_angle BETWEEN 8 AND 50)
            GROUP BY game_id, batter_id
        )
        SELECT 
            p.game_id,
            p.batter_id,
            AVG(p.launch_speed::NUMERIC) AS avg_exit_velocity,
            MAX(p.hit_distance_sc::NUMERIC) AS max_hit_distance,
            MAX(p.launch_speed::NUMERIC) AS top_exit_velocity,
            COALESCE(b.barrel_count::INTEGER, 0) AS total_barrels,
            SUM(p.delta_run_exp::NUMERIC) AS total_delta_run_exp
        FROM pitch_data p
        LEFT JOIN barrel_hits b
        ON p.game_id = b.game_id AND p.batter_id = b.batter_id
        WHERE p.game_date = '{target_date}'
        GROUP BY p.game_id, p.batter_id, b.barrel_count;
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error fetching pitch data: {e}")
        return pd.DataFrame()


def merge_daily_pitch_box(target_date=None):
    box_scores = load_s3_csv(BOX_SCORES_KEY)
    pitch_data = load_pitch_data_for_yesterday(target_date)
    existing_merged = load_s3_csv(MERGED_KEY)

    if pitch_data.empty or box_scores.empty:
        print(f"Missing data for {target_date}. Skipping merge.")
        return

    box_scores = box_scores.copy()
    box_scores["batter_id"] = box_scores["player_id"].str.replace("ID", "", regex=True).astype(int)
    box_scores.rename(columns={"game_pk": "game_id"}, inplace=True)

    pitch_data["game_id"] = pitch_data["game_id"].astype(int)
    pitch_data["batter_id"] = pitch_data["batter_id"].astype(int)
    box_scores["game_id"] = box_scores["game_id"].astype(int)

    merged = pitch_data.merge(box_scores, on=["game_id", "batter_id"])

    #Important fix
    merged["game_date"] = pd.to_datetime(target_date)

    merged_all = pd.concat([existing_merged, merged], ignore_index=True)
    merged_all.drop_duplicates(subset=["game_id", "batter_id"], keep="last", inplace=True)

    upload_s3_csv(merged_all, MERGED_KEY)


import os
import pandas as pd
import numpy as np
import boto3
from io import StringIO
from dotenv import load_dotenv

load_dotenv()

# AWS config
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
BUCKET = "baseball-data-mvp"
KEY = "mlb_game_data/merged_pitch_box_scores_2025.csv"  # Update to 2025 when ready


REGRESSION_WEIGHTS = {
    "hits": 0.1822,
    "doubles": 0.0968,
    "triples": 0.1849,
    "homeRuns": 0.3232,
    "rbi": -0.0300,
    "runs": -0.0181,
    "baseOnBalls": 0.1241,
    "hitByPitch": 0.1375,
    "strikeOuts": -0.0281,
    "groundIntoDoublePlay": -0.0229,
    "sacFlies": 0.1891,
    "stolenBases": -0.0032,
    "caughtStealing": 0.0085,
    "total_barrels": -0.0209,
    "avg_exit_velocity": 0.0012,
    "total_delta_run_exp": 0.0306
}

def load_merged_data():
    s3 = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    try:
        response = s3.get_object(Bucket=BUCKET, Key=KEY)
        return pd.read_csv(response["Body"])
    except Exception as e:
        print(f"Error loading data from S3: {e}")
        return None

def calculate_woba(df):
    woba_weights = {
        "BB": 0.689,
        "HBP": 0.720,
        "1B": 0.882,
        "2B": 1.254,
        "3B": 1.590,
        "HR": 2.050
    }

    df = df.copy()
    for col in ["baseOnBalls", "hitByPitch", "hits", "doubles", "triples", "homeRuns", "atBats", "sacFlies"]:
        df[col] = pd.to_numeric(df.get(col, 0), errors="coerce").fillna(0)

    singles = df["hits"] - df["doubles"] - df["triples"] - df["homeRuns"]

    numerator = (
        df["baseOnBalls"] * woba_weights["BB"] +
        df["hitByPitch"] * woba_weights["HBP"] +
        singles * woba_weights["1B"] +
        df["doubles"] * woba_weights["2B"] +
        df["triples"] * woba_weights["3B"] +
        df["homeRuns"] * woba_weights["HR"]
    )

    denominator = df["atBats"] + df["baseOnBalls"] - df["sacFlies"] + df["hitByPitch"]
    df["wOBA"] = numerator / denominator.replace(0, np.nan)
    df["wOBA"] = df["wOBA"].fillna(0)

    return df

def apply_game_score(df):
    df["regression_game_score"] = 50
    for feature, weight in REGRESSION_WEIGHTS.items():
        if feature in df.columns:
            df["regression_game_score"] += df[feature].fillna(0) * weight
    return df

def normalize_scores(df):
    mean_score = df["regression_game_score"].mean()
    std_score = df["regression_game_score"].std()
    df["scaled_game_score"] = ((df["regression_game_score"] - mean_score) / std_score) * 10 + 100
    df["scaled_game_score"] = df["scaled_game_score"].round(1)
    return df

def save_and_upload(df):
    s3 = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    s3.put_object(Bucket=BUCKET, Key=KEY, Body=csv_buffer.getvalue())
    print(f"Uploaded updated dataset with game scores to: s3://{BUCKET}/{KEY}")

def run_game_score_pipeline():
    df = load_merged_data()
    if df is None:
        return

    df = calculate_woba(df)
    df = apply_game_score(df)
    df = normalize_scores(df)
    save_and_upload(df)

run_game_score_pipeline()