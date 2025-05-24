import pandas as pd
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Config ---
DATA_DIR = "/Users/joshsteckler/PycharmProjects/baseball-mvp/situation_game_probability/data"
OUTPUT_PATH = os.path.join(DATA_DIR, "merged_statcast_2022_2024_with_stats.csv")
FILES = [
    "statcast_pitch_data_2022.csv",
    "statcast_pitch_data_2023.csv",
    "statcast_pitch_data_2024.csv"
]

# --- DB Config ---
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT", 5432)
}

# --- Load pitch files ---
def load_and_label_season(file_name):
    df = pd.read_csv(os.path.join(DATA_DIR, file_name))
    year = file_name.split("_")[-1].split(".")[0]
    df["season"] = int(year)
    return df

dfs = [load_and_label_season(f) for f in FILES]
df_all = pd.concat(dfs, ignore_index=True).drop_duplicates()

# --- Clean up types ---
df_all["game_date"] = pd.to_datetime(df_all["game_date"], errors="coerce")
df_all["inning"] = pd.to_numeric(df_all["inning"], errors="coerce")
for col in ["stand", "p_throws", "inning_topbot"]:
    if col in df_all.columns:
        df_all[col] = df_all[col].astype(str).str.upper()
df_all = df_all[df_all["batter_id"].notna() & df_all["pitcher_id"].notna()]

# pitcher stats
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    hitter_query = """
    SELECT
        season,
        key_mlbam AS batter_id,
        on_base_percentage,
        slugging_percentage,
        ops,
        iso,
        bb_percent,
        k_percent,
        wrc_plus
    FROM hitter_season_statistics;
    """
    cursor.execute(hitter_query)
    hitter_cols = [desc[0] for desc in cursor.description]
    hitter_data = cursor.fetchall()
    hitter_df = pd.DataFrame(hitter_data, columns=hitter_cols)

    # hitter stats
    pitcher_query = """
    SELECT
        season,
        key_mlbam AS pitcher_id,
        era,
        whip,
        k_per_9,
        bb_per_9,
        k_percent,
        bb_percent,
        fip,
        xfip,
        hr_per_9
    FROM season_pitching_statistics;
    """
    cursor.execute(pitcher_query)
    pitcher_cols = [desc[0] for desc in cursor.description]
    pitcher_data = cursor.fetchall()
    pitcher_df = pd.DataFrame(pitcher_data, columns=pitcher_cols)

    cursor.close()
    conn.close()
except Exception as e:
    print("❌ Error loading season stats from DB:", e)
    exit()


df_all["batter_id"] = pd.to_numeric(df_all["batter_id"], errors="coerce").astype("Int64")
df_all["pitcher_id"] = pd.to_numeric(df_all["pitcher_id"], errors="coerce").astype("Int64")

hitter_df["batter_id"] = pd.to_numeric(hitter_df["batter_id"], errors="coerce").astype("Int64")
pitcher_df["pitcher_id"] = pd.to_numeric(pitcher_df["pitcher_id"], errors="coerce").astype("Int64")
df_all = df_all.merge(hitter_df, how="left", on=["batter_id", "season"])
df_all = df_all.merge(pitcher_df, how="left", on=["pitcher_id", "season"])
df_all.to_csv(OUTPUT_PATH, index=False)
print(f"\nMerged dataset saved to:\n{OUTPUT_PATH}")
print(f"Total rows: {len(df_all):,}")

