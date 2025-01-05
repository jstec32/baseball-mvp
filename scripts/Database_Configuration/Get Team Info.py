import pandas as pd
from pybaseball import fielding

# File paths
fielding_path = "/docs/Fielding.csv"  # Update with your file path
people_path = "/docs/People.csv"  # Update with your file path

# Load CSVs
fielding_data = pd.read_csv(fielding_path,encoding='latin1')
people_data = pd.read_csv(people_path, encoding='latin1')

fielding_filtered = fielding_data[fielding_data['yearID'].between(2020, 2023)]

fielding_filtered = fielding_filtered.sort_values(by=['playerID', 'G'], ascending=[True, False])

fielding_relevant = fielding_filtered[['playerID', 'POS',"teamID"]].drop_duplicates(subset='playerID',keep='first')


people_data = people_data.drop_duplicates(subset='playerID', keep='first')

merged_data = fielding_relevant.merge(
    people_data[['playerID', 'nameFirst', 'nameLast', 'bbrefID', 'bats', 'throws']],
    on='playerID',
    how='inner'
)

merged_data = merged_data.rename(columns={
    'nameFirst': 'First Name',
    'nameLast': 'Last Name',
    'bbrefID': 'Baseball Reference ID',
    'bats': 'Bats',
    'throws': 'Throws',
    'POS': 'Position'
})

# Save to CSV
# Save the resulting dataset to the same directory as People.csv
save_path = "/docs/Player_Data_2020_2023.csv"
merged_data.to_csv(save_path, index=False)

print(f"Dataset saved to {save_path}")


# Display the first few rows
print(merged_data.head())






