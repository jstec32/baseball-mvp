import pandas as pd
import os
import glob
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import seaborn as sns

# Define the local directory where StatCast data is stored
data_dir = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/S3_Data"

# Get all CSV files from 2022, 2023, and 2024
csv_files = glob.glob(os.path.join(data_dir, "statcast_data_20*.csv"))

# Initialize an empty DataFrame
combined_data = pd.DataFrame()

# Load and merge all datasets
for file in csv_files:
    print(f"Processing file: {file}...")
    try:
        data_chunk = pd.read_csv(file, low_memory=False)
        combined_data = pd.concat([combined_data, data_chunk], ignore_index=True)
    except Exception as e:
        print(f"❌ Error loading {file}: {e}")

# Ensure the "pitch_type" column exists
if "pitch_type" not in combined_data.columns:
    raise ValueError("⚠️ 'pitch_type' column not found in dataset!")

# Count occurrences of each pitch type
pitch_counts = combined_data["pitch_type"].value_counts()

# Print the breakdown
print("\n📊 Pitch Type Distribution:")
print(pitch_counts)

# Plot the distribution
plt.figure(figsize=(12, 6))
sns.barplot(x=pitch_counts.index, y=pitch_counts.values, palette="Blues_r")
plt.xlabel("Pitch Type")
plt.ylabel("Count")
plt.title("Pitch Type Distribution in Dataset")
plt.xticks(rotation=45)
plt.close(fig)
