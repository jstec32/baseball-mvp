import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import os
from dotenv import load_dotenv

# Step 1: Load .env.local and environment variables
load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432)),
}

# Step 2: Load cleaned CSV
df = pd.read_csv("/Users/joshsteckler/PycharmProjects/baseball-mvp/backend/templates/mlb_40man_rosters_with_clean_fangraphs.csv")

# Clean and convert Fangraphs ID column
df["fangraphs_id"] = pd.to_numeric(df["fangraphs_id"], errors='coerce')


# Database credentials
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432)),
}

# Update the players table
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    update_sql = "UPDATE players SET idfg = '%s' WHERE key_mlbam = '%s'"

    for _, row in df.iterrows():
        fangraphs_id = row["fangraphs_id"]
        mlbam_id = row["player_id"]

        if pd.notnull(fangraphs_id) and fangraphs_id != -1:
            cursor.execute(update_sql, (int(fangraphs_id), int(mlbam_id)))

    conn.commit()
    print("✅ Database updated successfully.")
except Exception as e:
    print("❌ Database update failed:", e)
finally:
    cursor.close()
    conn.close()












