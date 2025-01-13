import pandas as pd
from pybaseball import statcast
from datetime import datetime, timedelta
import os

# Directory to save CSV files
csv_dir = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data"
os.makedirs(csv_dir, exist_ok=True)

# Function to fetch and process Statcast data for a single day
def fetch_statcast_data_for_day(date):
    try:
        print(f"Fetching Statcast data for {date}...")
        data = statcast(date, date)
        if data.empty:
            print(f"No data available for {date}.")
            return None
        print(f"Data fetched successfully for {date}.")
        return data
    except Exception as e:
        print(f"Error fetching data for {date}: {e}")
        return None

# Function to rename and filter columns to match the database schema
def process_statcast_data(data):
    """
    Rename and filter columns to match the database schema.
    """
    try:
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

        # Select only the columns required for the database
        columns_to_keep = [
            "game_id", "game_date", "inning", "inning_topbot", "pitcher_id", "batter_id",
            "pitch_type", "release_speed", "release_spin_rate", "release_pos_x", "release_pos_y", "release_pos_z",
            "pfx_x", "pfx_z", "plate_x", "plate_z", "zone", "events", "description", "launch_speed",
            "launch_angle", "hit_distance_sc", "effective_speed", "spin_axis", "stand", "p_throws"
        ]

        # Remove duplicate columns and select relevant ones
        data_filtered = data_renamed.loc[:, ~data_renamed.columns.duplicated()][columns_to_keep]

        # Replace NaN with None
        data_filtered = data_filtered.applymap(lambda x: None if pd.isna(x) else x)

        # Truncate 'inning_topbot' to fit VARCHAR(3)
        data_filtered['inning_topbot'] = data_filtered['inning_topbot'].str[:3]

        return data_filtered
    except Exception as e:
        print(f"Error processing data: {e}")
        return None

# Loop through each day and save data in monthly batches
def fetch_statcast_data_by_month(start_date, end_date):
    """
    Fetch Statcast data for each day in the given range and save monthly batches as CSVs.
    :param start_date: Start date (YYYY-MM-DD)
    :param end_date: End date (YYYY-MM-DD)
    """
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")

    monthly_data = []  # Accumulate data for the current month
    current_month = current_date.month

    while current_date <= end_date:
        day_data = fetch_statcast_data_for_day(current_date.strftime("%Y-%m-%d"))
        if day_data is not None:
            processed_data = process_statcast_data(day_data)
            if processed_data is not None:
                monthly_data.append(processed_data)

        # Move to the next day
        current_date += timedelta(days=1)

        # Check if we've moved to a new month
        if current_date.month != current_month or current_date > end_date:
            # Save the accumulated data for the current month
            if monthly_data:
                monthly_df = pd.concat(monthly_data, ignore_index=True)
                output_file = f"{csv_dir}/statcast_data_{current_date.year}_{current_month:02d}.csv"
                monthly_df.to_csv(output_file, index=False)
                print(f"Monthly data saved to {output_file}")

            # Reset for the new month
            monthly_data = []
            current_month = current_date.month

# Specify the date range
start_date = "2024-03-01"
end_date = "2024-11-20"

# Fetch and save data for each month in the range
fetch_statcast_data_by_month(start_date, end_date)
