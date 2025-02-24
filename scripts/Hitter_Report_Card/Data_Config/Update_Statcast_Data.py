import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

import os
import pandas as pd
load_dotenv()
# Define directory for updated 2024 Statcast files
directory_path = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/S3_Data/"

# Load all CSV files into a DataFrame
all_data = []
for file in os.listdir(directory_path):
    if file.endswith(".csv") and "2024" in file:
        file_path = os.path.join(directory_path, file)
        df = pd.read_csv(file_path)
        all_data.append(df)

# Combine into a single DataFrame
new_statcast_data = pd.concat(all_data, ignore_index=True)
print(f" Loaded {len(new_statcast_data)} rows from 2024 Statcast files.")

import psycopg2
from sqlalchemy import create_engine

statcast_columns = set(new_statcast_data.columns)
print(f" Statcast CSV Columns: {statcast_columns}")



# Load database credentials from .env
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT", 5432),
}

# Create connection
conn_str = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
engine = create_engine(conn_str)


def fetch_existing_data():
    query = """
    SELECT game_id, inning, batter_id, pitcher_id, game_date FROM pitch_data;
    """

    connection = psycopg2.connect(**DB_CONFIG)
    cursor = connection.cursor()

    try:
        cursor.execute(query)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return pd.DataFrame(results, columns=columns)
    except Exception as e:
        print(f" Error fetching existing data: {e}")
        return pd.DataFrame()
    finally:
        cursor.close()
        connection.close()


# Load existing data
existing_data = fetch_existing_data()
print(f" Retrieved {len(existing_data)} rows from database")
new_statcast_data["game_id"] = new_statcast_data["game_id"].astype(str)
existing_data["game_id"] = existing_data["game_id"].astype(str)
new_statcast_data["batter_id"] = new_statcast_data["game_id"].astype(str)
existing_data["batter_id"] = existing_data["game_id"].astype(str)
new_statcast_data["pitcher_id"] = new_statcast_data["game_id"].astype(str)
existing_data["pitcher_id"] = existing_data["game_id"].astype(str)
# Merge new data with existing data to determine inserts vs updates
merged_data = new_statcast_data.merge(
    existing_data,
    on=["game_id", "inning", "batter_id", "pitcher_id", "game_date"],
    how="left",
    indicator=True  # This creates a column `_merge` showing "both", "left_only", "right_only"
)

# Rows that exist in both datasets → UPDATE
update_data = merged_data[merged_data["_merge"] == "both"].drop(columns=["_merge"])
# Rows that are new → INSERT
insert_data = merged_data[merged_data["_merge"] == "left_only"].drop(columns=["_merge"])

print(f" Rows to insert: {len(insert_data)}, Rows to update: {len(update_data)}")

def insert_new_data(insert_data):
    """
    Inserts new rows into `pitch_data`.
    """
    if insert_data.empty:
        print(" No new rows to insert.")
        return

    values = [tuple(row) for row in insert_data.itertuples(index=False, name=None)]
    columns = [f'"{col}"' if col.lower() == "group" else col for col in insert_data.columns]

    query = f"""
    INSERT INTO pitch_data ({', '.join(columns)}) 
    VALUES %s;
    """

    connection = psycopg2.connect(**DB_CONFIG)
    cursor = connection.cursor()

    try:
        execute_values(cursor, query, values)
        connection.commit()
        print(f" Inserted {len(insert_data)} new rows")
    except Exception as e:
        print(f" Error inserting data: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()

# Run Insert
insert_new_data(insert_data)

def update_existing_data(update_data):
    """
    Updates existing rows in `pitch_data`.
    """
    if update_data.empty:
        print(" No rows to update.")
        return

    connection = psycopg2.connect(**DB_CONFIG)
    cursor = connection.cursor()

    try:
        for _, row in update_data.iterrows():
            update_columns = [f'"{col}"' if col.lower() == "group" else col for col in update_data.columns]

            query = f"""
            UPDATE pitch_data
            SET {', '.join([f"{col} = %s" for col in update_columns if col not in ["game_id", "inning", "batter_id", "pitcher_id", "game_date"]])}
            WHERE game_id = %s AND inning = %s AND batter_id = %s AND pitcher_id = %s AND game_date = %s;
            """
            cursor.execute(query, (*row.drop(["game_id", "inning", "batter_id", "pitcher_id", "game_date"]).values,
                                   row["game_id"], row["inning"], row["batter_id"], row["pitcher_id"], row["game_date"]))

        connection.commit()
        print(f" Updated {len(update_data)} existing rows")
    except Exception as e:
        print(f" Error updating data: {e}")
        connection.rollback()
    finally:
        cursor.close()
        connection.close()

# Run Update
update_existing_data(update_data)