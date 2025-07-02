import os
import json
from io import BytesIO

import pandas as pd
import psycopg2
import boto3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Postgres config
DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port":     int(os.getenv("DB_PORT", 5432)),
}

# S3 config
S3_BUCKET = "baseball-data-mvp"
S3_KEY    = "query_wrapper/2025_schema.json"

# Postgres tables to include
TABLES = [
    "pitcher_season_statistics",
    "hitter_season_statistics",
    "pitch_data",
    "pitcher_game_logs",
    "players",
    "teams",
    "pitcher_season_statistics"
]

# CSVs to include (logical name -> S3 key under mlb_game_data/)
CSV_SOURCES = {
    "merged_pitch_box_scores_2025": "mlb_game_data/merged_pitch_box_scores_2025.csv",
    "mlb_game_data_2025":            "mlb_game_data/mlb_game_data_2025.csv",
    "team_game_stats_2025.csv" : "mlb_game_data/team_game_stats_2025.csv"
}

def dump_and_upload_schema():
    # 1) Introspect Postgres tables
    conn   = psycopg2.connect(**DB_CONFIG)
    cur    = conn.cursor()
    schema = {}

    for tbl in TABLES:
        cur.execute("""
            SELECT column_name
              FROM information_schema.columns
             WHERE table_schema = 'public'
               AND table_name   = %s
             ORDER BY ordinal_position;
        """, (tbl,))
        schema[tbl] = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()

    # 2) Introspect CSV headers from S3
    s3 = boto3.client(
        "s3",
        aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name           = os.getenv("AWS_REGION", "us-east-1")
    )

    for name, key in CSV_SOURCES.items():
        obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
        # read only header row
        df = pd.read_csv(BytesIO(obj["Body"].read()), nrows=0)
        schema[name] = list(df.columns)

    # 3) Serialize and upload schema JSON
    schema_json = json.dumps(schema, indent=2)
    s3.put_object(
        Bucket      = S3_BUCKET,
        Key         = S3_KEY,
        Body        = schema_json,
        ContentType = "application/json"
    )

    print(f"Uploaded combined schema to s3://{S3_BUCKET}/{S3_KEY}")

if __name__ == "__main__":
    dump_and_upload_schema()
