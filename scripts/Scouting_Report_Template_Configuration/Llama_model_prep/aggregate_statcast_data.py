import pandas as pd
import os
from collections import defaultdict
import json


def aggregate_specific_matchup_data(csv_directory, output_path):
    """
    Aggregate specific matchup data for batter-pitcher pairs.
    """
    matchup_data = []
    for file in os.listdir(csv_directory):
        if file.endswith(".csv"):
            file_path = os.path.join(csv_directory, file)
            print(f"Processing file: {file}")
            data = pd.read_csv(file_path)

            # Group by batter-pitcher pair
            grouped = data.groupby(["batter_id", "pitcher_id"])

            for (batter_id, pitcher_id), group in grouped:
                total_pitches = len(group)
                most_common_pitch = group["pitch_type"].mode()[0] if not group["pitch_type"].mode().empty else None

                # Calculate zone distribution
                zone_distribution = (
                    group["zone"]
                    .value_counts(normalize=True)
                    .to_dict()
                )

                # Aggregate outcomes
                total_batted_balls = group[group["events"].notnull()].shape[0]

                # Append to matchup data
                matchup_data.append({
                    "batter_id": batter_id,
                    "pitcher_id": pitcher_id,
                    "total_pitches": total_pitches,
                    "most_common_pitch": most_common_pitch,
                    "zone_distribution": json.dumps(zone_distribution),  # Store as JSON for easy reading
                    "total_batted_balls": total_batted_balls
                })

    # Save aggregated data
    output_df = pd.DataFrame(matchup_data)
    output_file = os.path.join(output_path, "specific_matchup_data.csv")
    output_df.to_csv(output_file, index=False)
    print(f"Specific matchup data saved to: {output_file}")

def aggregate_similar_matchups(csv_directory, output_path):
    """
    Aggregate data for similar matchups based on player archetypes.
    """
    similar_matchup_data = []
    for file in os.listdir(csv_directory):
        if file.endswith(".csv"):
            file_path = os.path.join(csv_directory, file)
            print(f"Processing file: {file}")
            data = pd.read_csv(file_path)

            # Define archetypes: Example - Power hitters and High-spin pitchers
            data["hitter_archetype"] = data["launch_speed"].apply(lambda x: "Power Hitter" if x >= 95 else "Contact Hitter")
            data["pitcher_archetype"] = data["release_spin_rate"].apply(lambda x: "High Spin" if x >= 2500 else "Average Spin")

            grouped = data.groupby(["hitter_archetype", "pitcher_archetype"])

            for (hitter_type, pitcher_type), group in grouped:
                total_pitches = len(group)
                zone_distribution = group["zone"].value_counts(normalize=True).to_dict()

                similar_matchup_data.append({
                    "hitter_archetype": hitter_type,
                    "pitcher_archetype": pitcher_type,
                    "total_pitches": total_pitches,
                    "zone_distribution": json.dumps(zone_distribution)
                })

    # Save aggregated data
    output_df = pd.DataFrame(similar_matchup_data)
    output_file = os.path.join(output_path, "similar_matchup_data.csv")
    output_df.to_csv(output_file, index=False)
    print(f"Similar matchup data saved to: {output_file}")

def process_league_wide_trends(input_directory, output_directory):
    """
    Process league-wide trends data, cleaning blank 'pitch_type' rows and aggregating data.

    Args:
        input_directory (str): Path to the directory with input CSV files.
        output_directory (str): Path to save aggregated league-wide trends data.
    """
    os.makedirs(output_directory, exist_ok=True)

    aggregated_data = []

    for file in os.listdir(input_directory):
        if file.endswith(".csv"):
            input_path = os.path.join(input_directory, file)
            print(f"Processing file: {file}")

            try:
                # Read the CSV file
                df = pd.read_csv(input_path)

                # Remove rows where 'pitch_type' is blank
                before_rows = len(df)
                df = df[df['pitch_type'].notna()]
                after_rows = len(df)
                print(f"Removed {before_rows - after_rows} rows with blank 'pitch_type'.")

                # Aggregate league-wide trends
                grouped = df.groupby('pitch_type').agg({
                    'release_speed': 'mean',
                    'release_spin_rate': 'mean',
                    'pfx_x': 'mean',
                    'pfx_z': 'mean',
                    'plate_x': 'mean',
                    'plate_z': 'mean',
                    'zone': lambda x: x.value_counts(normalize=True).to_dict()
                }).reset_index()

                grouped.rename(columns={
                    'release_speed': 'avg_velocity',
                    'release_spin_rate': 'avg_spin_rate',
                    'pfx_x': 'avg_horizontal_break',
                    'pfx_z': 'avg_vertical_break',
                    'plate_x': 'avg_plate_x',
                    'plate_z': 'avg_plate_z',
                    'zone': 'zone_distribution'
                }, inplace=True)

                # Append the processed data for the current file
                aggregated_data.append(grouped)

            except Exception as e:
                print(f"Error processing {file}: {e}")

    # Combine all aggregated data and save to a single file
    if aggregated_data:
        combined_data = pd.concat(aggregated_data, ignore_index=True)
        output_path = os.path.join(output_directory, "league_wide_trends.csv")
        combined_data.to_csv(output_path, index=False)
        print(f"Aggregated league-wide trends saved to: {output_path}")
    else:
        print("No valid data processed.")

# Specify the directory containing the monthly CSVs and output file
csv_directory = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/S3_Data"
output_path = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/Historical_Data_3Layers"

# Run the aggregation function
aggregate_specific_matchup_data(csv_directory, output_path)
aggregate_similar_matchups(csv_directory, output_path)
process_league_wide_trends(csv_directory, output_path)

