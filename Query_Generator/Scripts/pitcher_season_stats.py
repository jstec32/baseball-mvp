import datetime
import os

import pandas as pd
from dotenv import load_dotenv
from pybaseball import pitching_stats
from sqlalchemy.dialects.postgresql import psycopg2

load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432))  # Default port 5432 if not set
}

PITCHER_COLS = {
    "IDfg":           "idfg",
    "Season":         "season",
    "Name":           "name",
    "Team":           "team",
    "Age":            "age",
    "W":              "wins",
    "L":              "losses",
    "ERA":            "era",
    "G":              "games",
    "GS":             "games_started",
    "SV":             "saves",
    "IP":             "innings_pitched",
    "H":              "hits_allowed",
    "ER":             "earned_runs",
    "HR":             "home_runs_allowed",
    "BB%":            "bb_percent",
    "K%":             "k_percent",
    "BB":             "walks",
    "SO":             "strikeouts",
    "WHIP":           "whip",
    "FIP":            "fip",
    "WAR":            "war"
}

def fetch_pitcher_stats(start_year, end_year, qual=1):
    dfs = []
    for yr in range(start_year, end_year + 1):
        print(f"Fetching pitcher stats for {yr}…")
        df = pitching_stats(yr, qual=qual)
        df['Season'] = yr
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

# 3. Filter + rename
def filter_pitcher_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = list(PITCHER_COLS.keys())
    missing = set(cols) - set(df.columns)
    if missing:
        raise KeyError(f"Missing raw columns: {missing}")
    out = df[cols].rename(columns=PITCHER_COLS)
    return out

# 4. Save CSV
def save_to_csv(df: pd.DataFrame, path: str):
    df.to_csv(path, index=False)
    print(f"Saved CSV to {path}")

# 5. Upsert to DB
def insert_pitcher_data_to_db(df: pd.DataFrame):
    cols = list(PITCHER_COLS.values())
    col_str = ", ".join(cols)
    val_placeholders = ", ".join(["%s"] * len(cols))
    conflict_update = ", ".join(
        f"{c}=EXCLUDED.{c}" for c in cols if c not in ("idfg","season")
    )
    sql = f"""
    INSERT INTO pitcher_season_statistics ({col_str})
    VALUES ({val_placeholders})
    ON CONFLICT (idfg, season) DO UPDATE SET {conflict_update};
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    for record in df[cols].itertuples(index=False, name=None):
        cur.execute(sql, record)
    conn.commit()
    cur.close()
    conn.close()
    print("Upsert complete.")

# 6. Main runner
def main_pitcher_season_stats(start_year, end_year, output_csv):
    raw = fetch_pitcher_stats(start_year, end_year, qual=1)
    clean = filter_pitcher_columns(raw)
    save_to_csv(clean, output_csv)
    insert_pitcher_data_to_db(clean)

if __name__ == "__main__":
    today = datetime.today().year
    main_pitcher_season_stats(2022, today, "pitcher_season_stats_2025.csv")