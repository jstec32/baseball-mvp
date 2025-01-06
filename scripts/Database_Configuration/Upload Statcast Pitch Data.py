import pandas as pd
from pybaseball import statcast
import psycopg2
from datetime import datetime, timedelta
import os

# Directory to save CSV files
csv_dir = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data"
os.makedirs(csv_dir, exist_ok=True)

# Function to fetch and insert data for a given date range
def fetch_and_save_statcast_data(start_date, end_date):
    try:
        print(f"Fetching Statcast data from {start_date} to {end_date}...")
        data = statcast(start_date, end_date)
        if data.empty:
            print(f"No data available for {start_date} to {end_date}.")
            return

        print("Data fetched successfully!")

        # Step 2: Rename columns to match the database schema
        data_renamed = data.rename(columns={
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
        })

        # Step 3: Select only the columns required for the database
        columns_to_keep = [
            "game_id", "game_date", "inning", "inning_topbot", "pitcher_id", "batter_id",
            "pitch_type", "release_speed", "release_spin_rate", "release_pos_x", "release_pos_y", "release_pos_z",
            "pfx_x", "pfx_z", "plate_x", "plate_z", "zone", "events", "description", "launch_speed",
            "launch_angle", "hit_distance_sc", "effective_speed", "spin_axis", "stand", "p_throws"
        ]

        # Remove duplicate columns from the DataFrame
        data_renamed = data_renamed.loc[:, ~data_renamed.columns.duplicated()]

        # Select only the columns required for the database
        data_filtered = data_renamed[columns_to_keep]

        # Step 4: Replace missing values (NaN) with None
        data_filtered = data_filtered.applymap(lambda x: None if pd.isna(x) else x)

        # Truncate 'inning_topbot' to fit VARCHAR(3) type
        data_filtered['inning_topbot'] = data_filtered['inning_topbot'].str[:3]

        # Step 5: Insert the processed data into the database
        output_file = f"{csv_dir}/statcast_data_{start_date}_to_{end_date}.csv"
        data_filtered.to_csv(output_file, index=False)
        print(f"Data saved to {output_file}")

    except Exception as e:
        print(f"Error processing data for {start_date} to {end_date}: {e}")

# Loop through date ranges (2020-2023) and fetch data in monthly chunks
start_year = 2021
end_year = 2023

for year in range(start_year, end_year + 1):
    for month in range(1, 13):
        start_date = datetime(year, month, 1).strftime("%Y-%m-%d")
        if month == 12:
            end_date = datetime(year, month, 31).strftime("%Y-%m-%d")
        else:
            end_date = (datetime(year, month + 1, 1) - timedelta(days=1)).strftime("%Y-%m-%d")
        fetch_and_save_statcast_data(start_date, end_date)

fetch_and_save_statcast_data('2020-04-01', '2020-04-31')