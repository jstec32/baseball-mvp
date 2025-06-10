
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
    "key_mlbam": "key_mlbam",
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



def get_db_columns() -> set:

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

    raw_keys = list(PITCHER_COLS.keys())
    df_cols  = set(df.columns)
    pg_cols  = get_db_columns()

    valid = {
        raw: dest
        for raw, dest in PITCHER_COLS.items()
        if (raw in df_cols) and (dest in pg_cols)
    }
    dropped = set(raw_keys) - set(valid.keys())
    if dropped:
        print("Dropping mappings for missing columns:", sorted(dropped))

    print("   → Columns before rename:", df.columns.tolist())
    print("   → Will keep & rename:", list(valid.keys()))

    out = df.loc[:, valid.keys()].rename(columns=valid)
    print("   → Columns after filtering + renaming:", out.columns.tolist())
    return out


def upsert_pitcher_data(df: pd.DataFrame):

    all_dest_cols = list(PITCHER_COLS.values())
    insert_cols   = [c for c in all_dest_cols if c in df.columns]

    col_str      = ", ".join(insert_cols)
    placeholders = ", ".join(["%s"] * len(insert_cols))
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

    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()
    for record in df[insert_cols].itertuples(index=False, name=None):
        cur.execute(sql, record)
    conn.commit()
    cur.close()
    conn.close()
    print("Upsert complete for columns:", insert_cols)


def fill_missing_key_mlbam(clean: pd.DataFrame, start_year: int) -> pd.DataFrame:

    # — Step A: forward‐fill/back‐fill any duplicates within the 2025 DataFrame —
    if "key_mlbam" in clean.columns:
        clean["key_mlbam"] = (
            clean
            .groupby("name")["key_mlbam"]
            .transform(lambda col: col.ffill().bfill())
        )

    # — Step B: find any rows that are still missing key_mlbam —
    missing_mask = clean["key_mlbam"].isna()
    if missing_mask.any():
        conn = psycopg2.connect(**DB_CONFIG)
        cur  = conn.cursor()

        cur.execute(f"""
            SELECT DISTINCT name, key_mlbam
              FROM pitcher_season_statistics
             WHERE season < {start_year}
               AND key_mlbam IS NOT NULL;
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if rows:
            df_prior   = pd.DataFrame(rows, columns=["name", "key_mlbam"])
            name_to_id = dict(zip(df_prior["name"], df_prior["key_mlbam"]))
        else:
            name_to_id = {}

        clean.loc[missing_mask, "key_mlbam"] = clean.loc[missing_mask, "name"].map(name_to_id)

        still_null = clean["key_mlbam"].isna().sum()
        if still_null:
            print(f"⚠️  After back‐filling from prior seasons, {still_null} rows still lack key_mlbam.")

    return clean


def fetch_pitcher_stats(start_year: int, end_year: int, players_df: pd.DataFrame, qual: int = 1) -> pd.DataFrame:
    """
    Fetch PyBaseball pitcher_stats(...) for each year in [start_year, end_year],
    add a 'key_mlbam' column by merging on players_df["full_name"], then return the concatenated DataFrame.
    """
    dfs = []
    for yr in range(start_year, end_year + 1):
        print(f"⏳  Fetching pitcher stats for {yr}…")
        df = pitching_stats(yr, qual=qual)
        df["Season"] = yr

        # Normalize the "Name" column (strip whitespace) so it matches players_df["full_name"]
        df["Name"] = df["Name"].str.strip()

        # Merge‐in key_mlbam by matching on the full name
        df = (
            df
            .merge(
                players_df[["full_name", "key_mlbam"]],
                how="left",
                left_on="Name",
                right_on="full_name"
            )
            .drop(columns=["full_name"])
        )

        print("   → Columns after name→key_mlbam join:", df.columns.tolist())
        dfs.append(df)

    return pd.concat(dfs, ignore_index=True)


def get_players_df() -> pd.DataFrame:

    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()
    cur.execute("""
        SELECT
            "First_Name",
            "Last_Name",
            key_mlbam
          FROM players
         WHERE key_mlbam IS NOT NULL;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    players_df = pd.DataFrame(rows, columns=["First_Name", "Last_Name", "key_mlbam"])
    players_df["full_name"] = (
        players_df["First_Name"].str.strip() + " " + players_df["Last_Name"].str.strip()
    )
    return players_df


def main_pitcher_season_stats(start_year: int, end_year: int):
    # 1) Load players_df first, so that you can map 'Name' → 'key_mlbam' in fetch_pitcher_stats(...)
    players_df = get_players_df()

    # 2) Fetch the raw PyBaseball data _and_ merge in `key_mlbam`
    raw = fetch_pitcher_stats(start_year, end_year, players_df, qual=1)

    # 3) Keep only those raw columns which actually exist in the Postgres schema, then rename them
    clean = filter_pitcher_columns(raw)

    # 4) Back‐fill any missing key_mlbam from prior seasons
    clean = fill_missing_key_mlbam(clean, start_year)

    # 5) Upsert everything back into Postgres
    upsert_pitcher_data(clean)


if __name__ == "__main__":
    # Run for 2025 only:
    main_pitcher_season_stats(2025, 2025)