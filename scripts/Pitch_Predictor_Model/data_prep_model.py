import os

import joblib
import pandas as pd
from sklearn.preprocessing import LabelEncoder, MinMaxScaler

# Initialize an empty DataFrame for combining data
combined_data = pd.DataFrame()

# Directory containing the CSV files
local_directory = '/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/S3_Data'

# Loop through files in the directory
for file_name in os.listdir(local_directory):
    if '2024' in file_name and file_name.endswith('.csv'):  # Check for "2024" in the filename
        file_path = os.path.join(local_directory, file_name)
        print(f"Processing file: {file_path}")

        # Read the CSV file into a DataFrame
        data = pd.read_csv(file_path)

        # Append the data to the combined DataFrame
        combined_data = pd.concat([combined_data, data], ignore_index=True)
print(f"Columns after loading data: {combined_data.columns}")

# Drop duplicates
combined_data = combined_data.drop_duplicates()


# Binary conversion for base runner columns
combined_data['on_3b'] = combined_data['on_3b'].apply(lambda x: 1 if x > 0 else 0)
combined_data['on_2b'] = combined_data['on_2b'].apply(lambda x: 1 if x > 0 else 0)
combined_data['on_1b'] = combined_data['on_1b'].apply(lambda x: 1 if x > 0 else 0)

# Encode runners on base
combined_data['runners_on'] = (combined_data['on_1b'] + combined_data['on_2b'] + combined_data['on_3b'] > 0).astype(int)

# One-hot encoding for categorical variables
combined_data = pd.get_dummies(combined_data, columns=['p_throws', 'stand', 'inning_topbot'], drop_first=True)

# One-hot encode the existing 'count' column
combined_data = pd.get_dummies(combined_data, columns=['count'], prefix='count', drop_first=True)

# Label encoding for pitch_type
encoder = LabelEncoder()
combined_data['pitch_type_encoded'] = encoder.fit_transform(combined_data['pitch_type'])

# Save the encoder for future use
joblib.dump(encoder, '/Users/joshsteckler/PycharmProjects/baseball-mvp/models/pitch_type_encoder.pkl')
print("Pitch type encoder saved successfully.")

pitch_type_mapping = {index: pitch for index, pitch in enumerate(encoder.classes_)}

print("Pitch Type Mapping:")
for key, value in pitch_type_mapping.items():
    print(f"{key}: {value}")

# Save the mapping to a CSV file
mapping_df = pd.DataFrame(list(pitch_type_mapping.items()), columns=['Encoded Value', 'Pitch Type'])
mapping_df.to_csv('/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/Pitch_Type_Mapping.csv', index=False)
print("Mapping saved to: Pitch_Type_Mapping.csv")


# Scale continuous features
scaler = MinMaxScaler()
continuous_features = ['release_speed', 'release_spin_rate', 'plate_x', 'plate_z', 'pfx_x', 'pfx_z']
combined_data[continuous_features] = scaler.fit_transform(combined_data[continuous_features])

# Add missing count columns with default value 0
expected_counts = [
    'count_0-0', 'count_1-0', 'count_1-1', 'count_1-2',
    'count_2-0', 'count_2-1', 'count_2-2',
    'count_3-0', 'count_3-1', 'count_3-2'
]
for col in expected_counts:
    if col not in combined_data.columns:
        combined_data[col] = 0

# Finalized feature set
final_columns = [
    'pitcher_id', 'p_throws_L', 'batter_id', 'stand_L',
    'count_1-0', 'count_1-1', 'count_1-2', 'count_2-0', 'count_2-1', 'count_2-2',
    'count_3-0', 'count_3-1', 'count_3-2', 'runners_on', 'on_1b', 'on_2b', 'on_3b',
    'release_speed', 'release_spin_rate', 'pfx_x', 'pfx_z', 'plate_x', 'plate_z',
    'inning', 'inning_topbot_BOT', 'outs_when_up'
]
target_column = 'pitch_type_encoded'

# Ensure all required columns are present
for col in final_columns + [target_column]:
    if col not in combined_data.columns:
        combined_data[col] = 0

# Filter the dataset to keep only necessary columns
filtered_data = combined_data[final_columns + [target_column]]

# Save the combined data to a new CSV
#output_file = '/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast_Model_Prepped.csv'
#filtered_data.to_csv(output_file, index=False)
#print(f"Combined data saved to: {output_file}")

from sklearn.model_selection import train_test_split

# 70-30 Split (stratify on pitch_type_encoded to maintain label proportions)
train_data, test_data = train_test_split(
    filtered_data,
    test_size=0.3,               # 30% test set
    shuffle=True,                # Shuffle to ensure unbiased splitting
    random_state=42,             # For reproducibility
    stratify=filtered_data['pitch_type_encoded']  # Maintain proportions of pitch types
)

# Verify proportions of pitch_type_encoded in train and test sets
print("Original data distribution:")
print(filtered_data['pitch_type_encoded'].value_counts(normalize=True))

print("\nTraining data distribution:")
print(train_data['pitch_type_encoded'].value_counts(normalize=True))

print("\nTesting data distribution:")
print(test_data['pitch_type_encoded'].value_counts(normalize=True))

# Save datasets to CSV for reference
train_data.to_csv('/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/Train_2024.csv', index=False)
test_data.to_csv('/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/Test_2024.csv', index=False)

print("Training and testing datasets saved.")