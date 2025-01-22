import pandas as pd
import os

def load_sort_flip_and_add_count_statcast_data_inplace(file_path):

    # Step 1: Load the CSV into a DataFrame
    statcast_data = pd.read_csv(file_path)

    # Step 2: Sort the data by game_date, game_id, inning, and inning_topbot
    statcast_data = statcast_data.sort_values(
        by=['game_date', 'game_id', 'inning', 'inning_topbot'],
        ascending=[True, True, True, False]
    )

    # Step 3: Reset the index for cleanliness
    statcast_data.reset_index(drop=True, inplace=True)

    # Step 4: Create a unique group ID for each batter-pitcher combination
    statcast_data['group'] = (
            (statcast_data['game_id'].astype(str) + '_' +
             statcast_data['inning'].astype(str) + '_' +
             statcast_data['inning_topbot'].astype(str) + '_' +
             statcast_data['pitcher_id'].astype(str) + '_' +
             statcast_data['batter_id'].astype(str))
            .factorize()[0] + 1
    )

    # Step 5: Flip the sequence within each group while maintaining group order
    statcast_data = statcast_data.groupby('group', group_keys=False).apply(lambda group: group.iloc[::-1])

    # Step 6: Add balls, strikes, and count columns
    def calculate_count(group):
        """Calculate running balls, strikes, and count for each group."""
        balls, strikes = 0, 0
        ball_strike_list = []

        for i, row in group.iterrows():
            if 'ball' in row['description'].lower():
                balls += 1
            elif row['description'].lower() in ['swinging_strike', 'called_strike', 'foul']:
                # Fouls only count as strikes if strikes < 2
                if strikes < 2 or row['description'].lower() != 'foul':
                    strikes += 1

            # Append the running count
            ball_strike_list.append((balls, strikes))

        group['balls'] = [x[0] for x in ball_strike_list]
        group['strikes'] = [x[1] for x in ball_strike_list]
        group['count'] = [f"{x[0]}-{x[1]}" for x in ball_strike_list]
        return group

    # Apply count calculation to each group
    statcast_data = statcast_data.groupby('group', group_keys=False).apply(calculate_count)

    # Step 5: Save the adjusted DataFrame to a new CSV file
    statcast_data.to_csv(file_path, index=False)
    print(f"Sorted and adjusted data saved to {file_path}")

    return statcast_data

# Directory containing the Statcast data files
directory_path = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/S3_Data/"

# Iterate over all files in the directory
for filename in os.listdir(directory_path):
    # Ensure we're only processing CSV files
    if filename.endswith(".csv"):
        file_path = os.path.join(directory_path, filename)
        # Process and update the file in place
        load_sort_flip_and_add_count_statcast_data_inplace(file_path)

print("All files processed and updated.")
