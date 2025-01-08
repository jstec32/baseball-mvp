import pandas as pd
from pybaseball import pitching_stats


# Fetch pitching data for the seasons 2019–2023
def fetch_pitching_stats(start_year, end_year, qual=25):
    print(f"Fetching pitching stats for seasons {start_year}-{end_year}...")
    data = pitching_stats(start_year, end_year, qual=qual)
    print(f"Fetched {len(data)} rows of data.")
    return data


# Filter the data to include only the required columns
def filter_columns(data):
    # Columns to keep based on the table schema
    columns_to_keep = {
        "IDfg": "idfg",
        "Season": "season",
        "Name": "name",
        "Team": "team",
        "Age": "age",
        "W": "wins",
        "L": "losses",
        "WAR": "war",
        "ERA": "era",
        "G": "games",
        "GS": "games_started",
        "IP": "innings_pitched",
        "SO": "strikeouts",
        "BB": "walks",
        "HR": "home_runs",
        "WHIP": "whip",
        "K/9": "k_per_9",
        "BB/9": "bb_per_9",
        "K%": "k_percent",
        "BB%": "bb_percent",
        "FIP": "fip",
        "xFIP": "xfip",
        "BABIP": "babip",
        "LOB%": "lob_percent",
        "HardHit%": "hard_hit_percent",
        "FB%": "fb_percent",
        "FBv": "fb_velocity",
        "SL%": "sl_percent",
        "SLv": "sl_velocity",
        "CH%": "ch_percent",
        "CHv": "ch_velocity",
        "CB%": "cb_percent",
        "CBv": "cb_velocity"
    }

    # Filter the data
    filtered_data = data[list(columns_to_keep.keys())]

    # Rename the columns to match the database schema
    filtered_data.rename(columns=columns_to_keep, inplace=True)
    print(f"Filtered data to include only the required columns.")
    return filtered_data

def add_primary_key(data):
    # Add a sequential index as the primary key
    data.insert(0, 'row_id', range(1, len(data) + 1))
    return data
# Save data to a specified file path
def save_to_csv(data, file_path):
    print(f"Saving data to {file_path}...")
    data.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}.")


# Main function
def main():
    # File path for CSV output
    file_path = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/season_pitching_statistics.csv"

    # Fetch pitching stats
    pitching_data = fetch_pitching_stats(2019, 2023, qual=25)

    # Filter the data
    #filtered_data = filter_columns(pitching_data)

    # Save to CSV
    save_to_csv(pitching_data, file_path)


if __name__ == "__main__":
    main()
