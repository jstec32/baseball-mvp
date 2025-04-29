import pandas as pd
from pybaseball import fielding, playerid_reverse_lookup
import os

def generate_player_data_2024(fielding_path, people_path, output_path):
    # Step 1: Load People data
    people_df = pd.read_csv(people_path, encoding='latin1')
    people_df = people_df.drop_duplicates(subset='playerID', keep='first')

    # Step 2: Load fielding data and filter for 2024
    fielding_df = pd.read_csv(fielding_path, encoding='latin1')
    fielding_2024 = fielding_df[fielding_df['yearID'] == 2024]

    if fielding_2024.empty:
        print("⚠️ No fielding data found for 2024. Try again later in the season.")
        return

    # Step 3: Get primary position & team for each player
    fielding_sorted = fielding_2024.sort_values(by=['playerID', 'G'], ascending=[True, False])
    fielding_relevant = fielding_sorted[['playerID', 'POS', 'teamID']].drop_duplicates(subset='playerID', keep='first')

    # Step 4: Merge with player info
    merged = fielding_relevant.merge(
        people_df[['playerID', 'nameFirst', 'nameLast', 'bbrefID', 'bats', 'throws']],
        on='playerID', how='inner'
    )

    merged = merged.rename(columns={
        'nameFirst': 'First Name',
        'nameLast': 'Last Name',
        'bbrefID': 'Baseball Reference ID',
        'bats': 'Bats',
        'throws': 'Throws',
        'POS': 'Position'
    })

    # Step 5: Use pybaseball to get MLBAM (Statcast) IDs
    bbref_ids = merged['Baseball Reference ID'].dropna().unique().tolist()
    lookup = playerid_reverse_lookup(bbref_ids, key_type='bbref')
    lookup_df = pd.DataFrame(lookup)

    # Step 6: Merge MLBAM IDs into main dataframe
    final_df = merged.merge(
        lookup_df[['key_bbref', 'key_mlbam']],
        left_on='Baseball Reference ID',
        right_on='key_bbref',
        how='left'
    )

    # Step 7: Save output
    final_df.to_csv(output_path, index=False)
    print(f"✅ Player dataset for 2024 saved to {output_path}")
    print(final_df.head())

# Example usage
generate_player_data_2024(
    fielding_path="/docs/Fielding.csv",
    people_path="/docs/People.csv",
    output_path="/docs/Player_Data_2024.csv"
)
