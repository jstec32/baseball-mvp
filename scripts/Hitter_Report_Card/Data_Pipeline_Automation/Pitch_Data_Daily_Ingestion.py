import pandas as pd
from pybaseball import statcast
from datetime import datetime, timedelta
import boto3
import psycopg2
import uuid
import os
from io import StringIO
from dotenv import load_dotenv
from datetime import datetime, timedelta
import requests
import pandas as pd
from io import StringIO

load_dotenv()

# --- CONFIG ---
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = "baseball-data-mvp"
LOG_FOLDER = "logs/statcast_ingestion"

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

def get_max_pitch_id():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(pitch_id) FROM pitch_data;")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result[0] is not None else 0
    except Exception as e:
        print(f"Error fetching max pitch_id: {e}")
        return 0
# --- STEP 1: Fetch Data ---
def fetch_statcast_data_for_day(date_str):
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        start_date = (target_date - timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = date_str

        url = (
            f"https://baseballsavant.mlb.com/statcast_search/csv?"
            f"all=true&type=details&player_type=pitcher"
            f"&game_date_gt={start_date}&game_date_lt={target_date}"
        )
        print(url)
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return None, f"Failed to fetch data (status {response.status_code})"

        df = pd.read_csv(StringIO(response.text))

        if df.empty:
            return None, f"No data returned for {date_str}"

        df["game_date"] = pd.to_datetime(df["game_date"])
        df = df[df["game_date"].dt.date == target_date]

        if df.empty:
            return None, f"No records in Statcast data for exact date {date_str}"

        return df, None

    except Exception as e:
        return None, f"Fetch error for {date_str}: {e}"

# --- STEP 2: Rename, Select, Fill Missing ---
def process_statcast_data(df_raw):
    rename_map = {
        "game_pk": "game_id",
        "pitcher": "pitcher_id",
        "batter": "batter_id",
        "pitch_name": "pitch_type",
        "release_speed": "release_speed",
        "release_spin_rate": "release_spin_rate",
        "release_pos_x": "release_pos_x",
        "release_pos_y": "release_pos_y",
        "release_pos_z": "release_pos_z",
        "pfx_x": "pfx_x",
        "pfx_z": "pfx_z",
        "plate_x": "plate_x",
        "plate_z": "plate_z",
        "zone": "zone",
        "events": "events",
        "description": "description",
        "launch_speed": "launch_speed",
        "launch_angle": "launch_angle",
        "hit_distance_sc": "hit_distance_sc",
        "effective_speed": "effective_speed",
        "spin_axis": "spin_axis",
        "stand": "stand",
        "p_throws": "p_throws",
        "inning": "inning",
        "inning_topbot": "inning_topbot",
        "game_date": "game_date",
        "on_1b": "on_1b",
        "on_2b": "on_2b",
        "on_3b": "on_3b",
        "outs_when_up": "outs_when_up",
        "hc_x": "hc_x",
        "hc_y": "hc_y",
        "woba_value": "woba_value",
        "woba_denom": "woba_denom",
        "delta_run_exp": "delta_run_exp",
        "delta_home_win_exp": "delta_home_win_exp",
    }

    full_column_list = list(rename_map.values()) + ["pitch_id", "group", "balls", "strikes", "count"]

    df = df_raw.rename(columns=rename_map)
    df = df.loc[:, ~df.columns.duplicated()]
    df = df[list(rename_map.keys())] if set(rename_map.keys()).issubset(df.columns) else df.rename(columns=rename_map)

    df["inning_topbot"] = df["inning_topbot"].str[:3]
    df = df.applymap(lambda x: None if pd.isna(x) else x)

    # Add pitch_id UUID
    df["pitch_id"] = [uuid.uuid4().hex for _ in range(len(df))]

    return df

# --- STEP 3: Add Group + Count Columns ---
def add_balls_strikes(df):
    # Create unique group identifier for each at-bat
    df["group"] = (
        df["game_id"].astype(str) + "_" +
        df["inning"].astype(str) + "_" +
        df["inning_topbot"].astype(str) + "_" +
        df["pitcher_id"].astype(str) + "_" +
        df["batter_id"].astype(str) + "_" +
        df["at_bat_number"].astype(str)  # Optional: more precise grouping
    ).factorize()[0] + 1

    # Sort pitches in natural order (first to last)
    df["inning_half_order"] = df["inning_topbot"].map({"Top": 0, "Bottom": 1})
    df = df.sort_values(
        ["game_date", "game_id", "inning", "inning_half_order", "at_bat_number", "pitch_number"]
    )
    df = df.drop('inning_half_order', axis=1)
    # Initialize columns
    df["balls"] = 0
    df["strikes"] = 0
    df["count"] = "0-0"

    # Track count progression
    def calculate_count(group):
        balls, strikes = 0, 0
        for idx, row in group.iterrows():
            if row["description"] in ["ball", "blocked_ball"]:
                balls += 1
            elif row["description"] in ["called_strike", "swinging_strike", "foul_tip"]:
                strikes += 1
            elif row["description"] == "foul" and strikes < 2:
                strikes += 1

            # Cap balls/strikes at 3/2 respectively
            balls = min(balls, 3)
            strikes = min(strikes, 2)

            group.at[idx, "balls"] = balls
            group.at[idx, "strikes"] = strikes
            group.at[idx, "count"] = f"{balls}-{strikes}"

        return group

    # Apply to each at-bat group
    df = df.groupby("group", group_keys=False).apply(calculate_count).reset_index(drop=True)

    return df

# --- STEP 4: Insert into Postgres ---
def insert_to_postgres(df):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cols = df.columns.tolist()
        quoted_cols = ', '.join([f'"{col}"' for col in cols])  # <-- Fix for SQL reserved words
        placeholders = ', '.join(['%s'] * len(cols))
        insert_sql = f'INSERT INTO pitch_data ({quoted_cols}) VALUES ({placeholders})'

        for row in df.itertuples(index=False):
            cursor.execute(insert_sql, tuple(row))

        conn.commit()
        cursor.close()
        conn.close()
        return None
    except Exception as e:
        return f"DB insert error: {e}"

# --- STEP 5: Upload log to S3 ---
def write_log_to_s3(log_text, date_str):
    key = f"{LOG_FOLDER}/{date_str}.log"
    s3 = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    s3.put_object(Body=log_text.encode("utf-8"), Bucket=AWS_BUCKET_NAME, Key=key)

def run_statcast_pipeline_for_date(target_date=None):

    if target_date is None:
        target_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    log = [f"Statcast pipeline run for {target_date}"]


    raw_data, err = fetch_statcast_data_for_day(target_date)

    if err:
        log.append(f"Error fetching data: {err}")
        return log
    elif raw_data is None or raw_data.empty:
        log.append("No data returned from Statcast API.")
        return log


    df = process_statcast_data(raw_data)
    df = add_balls_strikes(df)


    required_columns = [
        'pitch_id', 'game_id', 'game_date', 'inning', 'inning_topbot',
        'pitcher_id', 'batter_id', 'pitch_type', 'release_speed', 'release_spin_rate',
        'release_pos_x', 'release_pos_y', 'release_pos_z', 'pfx_x', 'pfx_z',
        'plate_x', 'plate_z', 'zone', 'events', 'description', 'launch_speed',
        'launch_angle', 'hit_distance_sc', 'effective_speed', 'spin_axis', 'stand',
        'p_throws', 'group', 'balls', 'strikes', 'count', 'hc_y', 'outs_when_up',
        'hc_x', 'on_1b', 'woba_value', 'delta_run_exp', 'on_3b', 'on_2b',
        'woba_denom', 'delta_home_win_exp'
    ]
    for col in required_columns:
        if col not in df.columns:
            df[col] = None
    df = df[required_columns].reset_index(drop=True)


    start_id = get_max_pitch_id()
    df["pitch_id"] = df.index + 1 + start_id


    output_path = f"statcast_pitch_data_{target_date}.csv"
    df.to_csv(output_path, index=False)
    log.append(f"CSV saved to {output_path}")


    db_error = insert_to_postgres(df)
    if db_error:
        log.append(f"Database insert error: {db_error}")
    else:
        log.append("Data inserted successfully.")


    final_log = "\n".join(log)
    print(final_log)
    write_log_to_s3(final_log, target_date)

    return log