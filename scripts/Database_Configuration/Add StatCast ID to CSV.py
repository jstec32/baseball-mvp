import pandas as pd
from pybaseball import playerid_reverse_lookup

# File path to your CSV
csv_file_path = '/docs/Player_Data_2020_2023.csv'

# Step 1: Read the CSV file
df = pd.read_csv(csv_file_path)

# Ensure your Baseball Reference ID column is correctly named
baseball_reference_column = 'Baseball Reference ID'  # Update this to the actual column name
if baseball_reference_column not in df.columns:
    raise ValueError(f"Column '{baseball_reference_column}' not found in the CSV.")

# Step 2: Extract Baseball Reference IDs
player_ids = df[baseball_reference_column].dropna().tolist()

# Step 3: Retrieve key_mlbam values using pybaseball
lookup_data = playerid_reverse_lookup(player_ids, key_type='bbref')

# Convert the returned data to a DataFrame
lookup_df = pd.DataFrame(lookup_data)

# Merge the new data with the existing DataFrame
df_updated = df.merge(lookup_df[['key_bbref', 'key_mlbam']], 
                      left_on=baseball_reference_column, 
                      right_on='key_bbref', 
                      how='left')

# Step 4: Save the updated DataFrame back to CSV
df_updated.to_csv(csv_file_path, index=False)

print(f"CSV file updated successfully at {csv_file_path}.")
