import pandas as pd
import glob

# Define the directory and file pattern
file_path_pattern = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/S3_Data/statcast_data_2024_*.csv"

# Get all CSV files that contain '2024' in the filename
csv_files = glob.glob(file_path_pattern)

print(f"Found {len(csv_files)} files to process.")

# Iterate over each file and clean duplicates
for file in csv_files:
    print(f"Processing file: {file}")

    # Read the CSV file
    df = pd.read_csv(file)

    # Drop exact duplicate rows
    df_cleaned = df.drop_duplicates()

    # Save back to the same file (overwrite)
    df_cleaned.to_csv(file, index=False)

    print(f"Cleaned {file}: {len(df) - len(df_cleaned)} duplicate rows removed.")

print(" All files processed successfully!")
