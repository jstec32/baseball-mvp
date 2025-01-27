import pandas as pd
import os

# Define file paths
original_file_path = '/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/S3_Data/statcast_data_2024_11.csv'  # Replace with the path to your original dataset
new_file_path = '/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/statcast_data_2024_11.csv'  # Replace with the path to the dataset with runner/outs data

# Load the datasets
original_data = pd.read_csv(original_file_path)
new_data = pd.read_csv(new_file_path)

# Columns to merge from the new dataset
columns_to_merge = ['game_id', 'game_date', 'inning', 'inning_topbot', 'pitcher_id', 'batter_id',
                    'on_3b', 'on_2b', 'on_1b', 'outs_when_up']

# Filter the new dataset to only include relevant columns
new_data_filtered = new_data[columns_to_merge]

# Merge datasets on the shared keys
merged_data = pd.merge(
    original_data,
    new_data_filtered,
    on=['game_id', 'game_date', 'inning', 'inning_topbot', 'pitcher_id', 'batter_id'],
    how='left'  # Use 'left' to retain all rows from the original dataset
)

# Save the merged dataset back to a CSV for inspection
output_file_path = '/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/S3_Data/statcast_data_2024_11.csv'  # Replace with your desired output path
merged_data.to_csv(output_file_path, index=False)
print(f"Merged dataset saved to: {output_file_path}")