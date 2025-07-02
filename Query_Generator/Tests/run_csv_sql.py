import os
import duckdb
import boto3
import pandas as pd
from io import BytesIO
from dotenv import load_dotenv
from sqlalchemy import create_engine
import sqlparse

load_dotenv()  # make sure your .env has DB_HOST, DB_NAME, etc.

#
# ────────────────────────────────────────────────────────
# 1) PostgreSQL CONFIGURATION
# ────────────────────────────────────────────────────────
#
DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port":     int(os.getenv("DB_PORT", 5432)),
}

# Build a SQLAlchemy URL so we can read Postgres tables into pandas
PG_URL = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)
pg_engine = create_engine(PG_URL)



S3_BUCKET = "baseball-data-mvp"
CSV_SOURCES = {
    "merged_pitch_box_scores_2025": "mlb_game_data/merged_pitch_box_scores_2025.csv",
    "mlb_game_data_2025":            "mlb_game_data/mlb_game_data_2025.csv",
    "team_game_stats_2025": "mlb_game_data/team_game_stats_2025.csv"
}

s3 = boto3.client(
    "s3",
    aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name           = os.getenv("AWS_REGION", "us-east-1")
)


def load_csv_from_s3_to_duck(con: duckdb.DuckDBPyConnection, table_name: str, s3_key: str):

    print(f"⏳  Downloading “{s3_key}” from S3 bucket “{S3_BUCKET}”...")
    obj = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
    df_csv = pd.read_csv(BytesIO(obj["Body"].read()))

    # If there is a game_date column, coerce/normalize it:
    if "game_date" in df_csv.columns:
        df_csv["game_date"] = pd.to_datetime(
            df_csv["game_date"], errors="coerce", infer_datetime_format=True
        )

        missing = df_csv["game_date"].isna().sum()
        if missing:
            print(f"Filling {missing} missing game_date rows with 2025‑04‑01")
            df_csv["game_date"].fillna(pd.Timestamp("2025-04-01"), inplace=True)

    con.register(table_name, df_csv)
    print(f"Registered CSV as DuckDB view “{table_name}”.")


def load_postgres_table_to_duck(con: duckdb.DuckDBPyConnection, table_name: str):

    print(f"Pulling Postgres table “{table_name}” into pandas...")
    df = pd.read_sql(f"SELECT * FROM {table_name}", pg_engine)
    con.register(table_name, df)
    print(f"Registered Postgres table “{table_name}” as DuckDB view.")


if __name__ == "__main__":

    con = duckdb.connect()
    for tbl, s3_key in CSV_SOURCES.items():
        load_csv_from_s3_to_duck(con, tbl, s3_key)

    PG_TABLES = [
        "players",
        "teams",
        "pitcher_season_statistics",
        "hitter_season_statistics",
        "pitcher_game_logs",
        "pitch_data"
        # add more Postgres table names here if needed…
    ]
    for tbl in PG_TABLES:
        load_postgres_table_to_duck(con, tbl)

    print("All tables (CSV‑backed + Postgres) are now loaded into DuckDB.\n")

    user_sql = """
 SELECT
  game_id,
  game_date,
  home_team,
  home_score,
  away_team,
  away_score
FROM mlb_game_data_2025
WHERE game_date::DATE = '2025-06-26'
  AND ('Seattle Mariners' = home_team OR 'Seattle Mariners' = away_team) 

"""

    # ──────────────────────────────────────────────────────────────────────────
    # 5) Validate that it is exactly one SELECT statement, then execute
    # ──────────────────────────────────────────────────────────────────────────
    try:
        parsed = sqlparse.parse(user_sql)
        if len(parsed) != 1 or parsed[0].get_type().upper() != "SELECT":
            raise ValueError("🔴 Only a single SELECT statement is allowed.")
    except Exception as e:
        print(f"\n❌  Invalid SQL: {e}")
        exit(1)

    # ──────────────────────────────────────────────────────────────────────────
    # 6) Run it in DuckDB and print the resulting DataFrame (or a zero‑row notice)
    # ──────────────────────────────────────────────────────────────────────────
    try:
        df_res = con.execute(user_sql).df()
        if df_res.empty:
            print("Query ran successfully but returned zero rows.")
        else:
            print("\nQuery result:\n")
            print(df_res.to_string(index=False))
            print()
    except Exception as e:
        print(f"\nError executing SQL:\n    {e}\n")
        exit(1)
