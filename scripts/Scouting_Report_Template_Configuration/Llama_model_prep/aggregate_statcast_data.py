import os
import pandas as pd


def aggregate_statcast_data_by_year(csv_dir, output_dir):
    """
    Aggregate Statcast data by year, summarizing batter-pitcher matchups.
    """
    yearly_stats = {}

    for file_name in os.listdir(csv_dir):
        if file_name.endswith(".csv"):
            try:
                year = file_name.split("_")[2]  # Extract year from filename
                file_path = os.path.join(csv_dir, file_name)
                print(f"Processing file: {file_name}")

                # Read CSV
                data = pd.read_csv(file_path)

                # Clean and prepare the data
                data = data.dropna(subset=['pitch_type', 'description'])  # Ensure valid rows
                data['is_batted_ball'] = data['events'].notna()

                # Group and aggregate data
                grouped = data.groupby(['batter_id', 'pitcher_id']).agg({
                    'game_id': 'count',  # Total pitches
                    'release_speed': 'mean',  # Average velocity
                    'release_spin_rate': 'mean',  # Average spin rate
                    'pfx_x': 'mean',  # Average horizontal break
                    'pfx_z': 'mean',  # Average vertical break
                    'plate_x': 'mean',  # Average plate x location
                    'plate_z': 'mean',  # Average plate z location
                    'is_batted_ball': 'sum',  # Total batted balls
                    'pitch_type': lambda x: x.value_counts().idxmax(),  # Most common pitch type
                    'zone': lambda x: x.value_counts(normalize=True).to_dict(),  # Zone distribution
                }).reset_index()

                # Rename columns for clarity
                grouped = grouped.rename(columns={
                    'game_id': 'total_pitches',
                    'release_speed': 'avg_velocity',
                    'release_spin_rate': 'avg_spin_rate',
                    'pfx_x': 'avg_horizontal_break',
                    'pfx_z': 'avg_vertical_break',
                    'plate_x': 'avg_plate_x',
                    'plate_z': 'avg_plate_z',
                    'is_batted_ball': 'total_batted_balls',
                    'pitch_type': 'most_common_pitch',
                    'zone': 'zone_distribution'
                })

                # Aggregate per year
                if year not in yearly_stats:
                    yearly_stats[year] = []
                yearly_stats[year].append(grouped)

            except Exception as e:
                print(f"Error processing file {file_name}: {e}")
                continue

    # Combine and save yearly stats
    for year, stats_list in yearly_stats.items():
        combined_data = pd.concat(stats_list, ignore_index=True)
        output_file = os.path.join(output_dir, f"aggregated_statcast_{year}.csv")
        combined_data.to_csv(output_file, index=False)
        print(f"Aggregated data for {year} saved to {output_file}")



# Specify the directory containing the monthly CSVs and output file
csv_directory = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/S3_Data"
output_directory = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/agg_data"

# Run the aggregation function
aggregate_statcast_data_by_year(csv_directory, output_directory)

