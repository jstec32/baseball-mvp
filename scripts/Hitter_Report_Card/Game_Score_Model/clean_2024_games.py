import boto3
import pandas as pd
import os
from io import StringIO
import psycopg2
from dotenv import load_dotenv

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = "baseball-data-mvp"
MLB_GAME_DATA_PATH = "mlb_game_data/2024_full_box_scores.csv"
load_dotenv()

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT", 5432)
}

def load_box_scores_from_s3():
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )

    try:
        response = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=MLB_GAME_DATA_PATH)
        csv_content = response['Body'].read().decode('utf-8')
        box_scores_df = pd.read_csv(StringIO(csv_content))
        print(f"Loaded {len(box_scores_df)} game records from S3.")
        print(box_scores_df.columns)
        return box_scores_df

    except Exception as e:
        print(f"Error fetching box scores from S3: {e}")
        return None

# Load the box scores
box_scores_df = load_box_scores_from_s3()

import psycopg2
import pandas as pd


# Load aggregated pitch data with barrel calculations
def load_aggregated_pitch_data():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        query = """
        WITH at_bat_max_hits AS (
    SELECT
        game_id,
        batter_id,
        pitch_data."group",
        MAX(launch_speed) AS max_launch_speed,  -- Hardest-hit ball per at-bat
        MAX(launch_angle) AS max_launch_angle
    FROM pitch_data
    WHERE description = 'hit_into_play'
    GROUP BY game_id, batter_id, pitch_data."group"
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
GROUP BY p.game_id, p.batter_id, b.barrel_count;
        """
        pitch_agg_df = pd.read_sql(query, conn)
        conn.close()

        print(f"Loaded {len(pitch_agg_df)} aggregated pitch records.")
        return pitch_agg_df

    except Exception as e:
        print(f"Error loading aggregated pitch data: {e}")
        return None



# Merge Pitch Data with Box Scores
def merge_pitch_and_box_scores():
    # Load datasets
    box_scores_df = load_box_scores_from_s3()
    pitch_agg_df = load_aggregated_pitch_data()

    if box_scores_df is None or pitch_agg_df is None:
        print("Error: One or more datasets failed to load.")
        return None

    # Clean box scores player_id: Remove "ID_" prefix and convert to integer
    box_scores_df["batter_id"] = box_scores_df["player_id"].str.replace("ID", "", regex=True).astype(int)

    # Rename 'game_pk' to 'game_id' in box scores for consistency
    box_scores_df.rename(columns={"game_pk": "game_id"}, inplace=True)
    # Ensure 'game_id' and 'batter_id' are integers in both DataFrames
    pitch_agg_df["game_id"] = pitch_agg_df["game_id"].astype(int)
    pitch_agg_df["batter_id"] = pitch_agg_df["batter_id"].astype(int)

    box_scores_df["game_id"] = box_scores_df["game_id"].astype(int)
    box_scores_df["batter_id"] = box_scores_df["batter_id"].astype(int)
    # Merge datasets on game_id and batter_id
    merged_df = pitch_agg_df.merge(box_scores_df, on=["game_id", "batter_id"])
    output_csv_path = "merged_pitch_box_scores.csv"
    merged_df.to_csv(output_csv_path, index=False)
    print(f"Saved merged dataset to {output_csv_path}")

    print(f"Final dataset contains {len(merged_df)} records.")
    return merged_df

# Run the merge function
final_data = merge_pitch_and_box_scores()