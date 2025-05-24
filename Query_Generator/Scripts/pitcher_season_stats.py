
import os
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from pybaseball import pitching_stats
import psycopg2
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
    "IDfg":            "idfg",
    "Season":          "season",
    "Name":            "name",
    "Team":            "team",
    "Age":             "age",
    "W":               "wins",
    "L":               "losses",
    "ERA":             "era",
    "G":               "games",
    "GS":              "games_started",
    "SV":              "saves",
    "IP":              "innings_pitched",
    "H":               "hits_allowed",
    "ER":              "earned_runs",
    "HR":              "home_runs_allowed",
    "BB%":             "bb_percent",
    "K%":              "k_percent",
    "BB":              "walks",
    "SO":              "strikeouts",
    "WHIP":            "whip",
    "FIP":             "fip",
    "WAR":             "war",

    # rate/context metrics
    "K/9":             "strikeouts_per_nine",
    "BB/9":            "walks_per_nine",
    "K/BB":            "k_to_bb_ratio",
    "H/9":             "hits_per_nine",
    "HR/9":            "home_runs_per_nine",
    "ERA-":            "era_minus",
    "xFIP":            "xfip",
    "xFIP-":           "xfip_minus",
    "BABIP":           "babip",
    "LOB%":            "lob_percent",
    "GB/FB":           "gb_fb_ratio",
    "LD%":             "ld_percent",
    "GB%":             "groundball_percent",
    "FB%":             "flyball_percent",
    "HR/FB":           "hr_fb_ratio",
    "FIP-":            "fip_minus",
    "SIERA":           "siera"
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
import logging

def get_db_columns():
    """
    Fetch list of real columns on pitcher_season_statistics
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()
    cur.execute("""
        SELECT column_name
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name   = 'pitcher_season_statistics';
    """)
    cols = {row[0] for row in cur.fetchall()}
    cur.close()
    conn.close()
    return cols

def filter_pitcher_columns(df: pd.DataFrame) -> pd.DataFrame:
    # what we *asked* to map:
    raw_keys = list(PITCHER_COLS.keys())
    # what we actually pulled:
    df_cols  = set(df.columns)
    # what Postgres actually has:
    pg_cols  = get_db_columns()

    # only keep mappings where raw in df *and* dest in pg
    valid = {
        raw: dest
        for raw, dest in PITCHER_COLS.items()
        if raw in df_cols and dest in pg_cols
    }
    dropped = set(raw_keys) - set(valid.keys())
    if dropped:
        print("Dropping mappings for missing columns:", sorted(dropped))

    # subset + rename
    out = (
        df
        .loc[:, valid.keys()]
        .rename(columns=valid)
    )
    return out


# 4. Save CSV
def save_to_csv(df: pd.DataFrame, path: str):
    df.to_csv(path, index=False)
    print(f"Saved CSV to {path}")

# 5. Upsert to DB
def insert_pitcher_data_to_db(df: pd.DataFrame):
    # 1) Only insert the columns that exist in df
    all_dest_cols = list(PITCHER_COLS.values())
    insert_cols = [c for c in all_dest_cols if c in df.columns]

    # 2) Build SQL with only those columns
    col_str = ", ".join(insert_cols)
    placeholders = ", ".join(["%s"] * len(insert_cols))
    # Exclude idfg & season from updates
    conflict_set = ", ".join(
        f"{c}=EXCLUDED.{c}"
        for c in insert_cols
        if c not in ("idfg", "season")
    )
    sql = f"""
    INSERT INTO pitcher_season_statistics ({col_str})
    VALUES ({placeholders})
    ON CONFLICT (idfg, season) DO UPDATE SET {conflict_set};
    """

    # 3) Execute
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    for record in df[insert_cols].itertuples(index=False, name=None):
        cur.execute(sql, record)
    conn.commit()
    cur.close()
    conn.close()
    print("Upsert complete for columns:", insert_cols)


# 6. Main runner
def main_pitcher_season_stats(start_year, end_year, output_csv):
    raw = fetch_pitcher_stats(start_year, end_year, qual=1)
    clean = filter_pitcher_columns(raw)
    save_to_csv(clean, output_csv)
    insert_pitcher_data_to_db(clean)

if __name__ == "__main__":
    today = datetime.today().year
    main_pitcher_season_stats(2025, 2025, "pitcher_season_stats_2025.csv")