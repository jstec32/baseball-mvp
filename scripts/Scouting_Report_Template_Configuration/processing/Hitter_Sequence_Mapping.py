import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

def analyze_pitch_sequences_from_sample(file_path, batter_id=None, pitcher_id=None):
    """
    Analyze pitch sequencing and hitter/pitcher performance by count using sample Statcast data,
    optionally filtering for a specific batter and pitcher.

    Args:
        file_path (str): Path to the sample Statcast CSV file.
        batter_id (int, optional): Specific batter ID to filter the data. Defaults to None.
        pitcher_id (int, optional): Specific pitcher ID to filter the data. Defaults to None.

    Outputs:
        Visualizations of pitch sequencing and performance by count.
    """
    # Load the sample Statcast data
    data = pd.read_csv(file_path)

    # Filter for specific batter and/or pitcher if provided
    if batter_id is not None:
        data = data[data['batter_id'] == batter_id]
    if pitcher_id is not None:
        data = data[data['pitcher_id'] == pitcher_id]

    # Step 1: Derive balls and strikes based on the 'description' column
    data['balls'] = data['description'].apply(lambda x: 1 if 'ball' in x.lower() else 0).cumsum()
    data['strikes'] = data['description'].apply(
        lambda x: 1 if x.lower() in ['swinging_strike', 'called_strike', 'foul'] else 0).cumsum()

    # Step 2: Create a count_state column
    data['count_state'] = data['balls'].astype(str) + '-' + data['strikes'].astype(str)

    # Step 3: Aggregate hitter performance by count
    hitter_performance = data.groupby('count_state').agg(
        BA=('launch_speed', lambda x: (x.notna().sum() / max(x.count(), 1))),  # Avoid division by zero
        SLG=('launch_speed', lambda x: x.sum() / max(x.count(), 1)),  # Avoid division by zero
        Whiff_Rate=('description', lambda x: (x == 'swinging_strike').sum() / max(x.count(), 1))  # Avoid division by zero
    ).reset_index()

    # Step 4: Aggregate pitcher performance by count and pitch type
    pitcher_performance = data.groupby(['count_state', 'pitch_type']).agg(
        Whiff_Rate=('description', lambda x: (x == 'swinging_strike').sum() / max(x.count(), 1)),  # Avoid division by zero
        BAA=('events', lambda x: (x == 'hit_into_play').sum() / max(x.count(), 1))  # Avoid division by zero
    ).reset_index()

    # Step 5: Visualize pitch sequencing by count
    print("Generating Pitch Sequencing Heatmap...")
    if not pitcher_performance.empty:
        sequence_pivot = pitcher_performance.pivot(index='count_state', columns='pitch_type', values='Whiff_Rate')
        sns.heatmap(sequence_pivot, annot=True, cmap="Blues", fmt=".2f")
        plt.title('Pitch Sequencing by Count (Whiff Rate)')
        plt.xlabel('Pitch Type')
        plt.ylabel('Count State')
        plt.show()
    else:
        print("No data available for the selected pitcher.")

    # Step 6: Visualize hitter performance by count
    print("Generating Hitter Performance Chart...")
    if not hitter_performance.empty:
        hitter_performance.plot(x='count_state', y=['BA', 'SLG', 'Whiff_Rate'], marker='o')
        plt.title('Hitter Performance by Count')
        plt.xlabel('Count State')
        plt.ylabel('Metrics')
        plt.legend(['BA', 'SLG', 'Whiff Rate'])
        plt.grid()
        plt.show()
    else:
        print("No data available for the selected batter.")

    # Return computed DataFrames for further use
    return hitter_performance, pitcher_performance


# File path provided
file_path = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/S3_Data/statcast_data_2024_09.csv"

# Example usage with specific batter and pitcher IDs
specific_batter_id = "605400"  # Replace with the actual batter ID
specific_pitcher_id = "518692"  # Replace with the actual pitcher ID

# Analyze the sample data
hitter_perf_sample, pitcher_perf_sample = analyze_pitch_sequences_from_sample(
    file_path,
    batter_id=specific_batter_id,
    pitcher_id=specific_pitcher_id
)
