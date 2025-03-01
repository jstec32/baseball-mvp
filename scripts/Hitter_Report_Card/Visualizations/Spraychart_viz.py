import os
from io import StringIO

import pandas as pd
import psycopg2
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from pybaseball import statcast_single_game
from scripts.Hitter_Report_Card.Data_Config.Spraychart_dev import spraychart_final
import boto3
# Load .env file
load_dotenv()  # Ensure environment variables are loaded correctly

# AWS Configuration
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
# S3 Bucket Variables
SCOUTING_REPORTS_S3_BUCKET = os.getenv("SCOUTING_REPORTS_S3_BUCKET")
MODEL_TRAINING_S3_BUCKET = os.getenv("MODEL_TRAINING_S3_BUCKET")
STATCAST_S3_BUCKET = os.getenv("STATCAST_S3_BUCKET")  # Now using a separate bucket for Statcast
STATCAST_S3_PATH = os.getenv("STATCAST_S3_PATH")

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432))  # Default port 5432 if not set
}

# Initialize S3 Client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)


# User input: Filter based on game_date & batter_id
game_date = "2024-10-01"  # Example game date
batter_id = 624585  # Example player ID (Julio Rodríguez)


def load_statcast_data_from_s3():
    """ Fetches all Statcast 2024 monthly files from S3 and loads them into a Pandas DataFrame """
    statcast_data = []

    try:
        # Get all objects in the S3 bucket
        response = s3_client.list_objects_v2(Bucket=STATCAST_S3_BUCKET)

        if "Contents" not in response:
            print("No Statcast data found in S3.")
            return pd.DataFrame()

        # Iterate through all objects and filter only 2024 CSV files
        for obj in response["Contents"]:
            file_key = obj["Key"]

            # Ensure it's a file (not a folder) and follows the `statcast_data_2024_XX.csv` pattern
            if file_key.endswith(".csv") and "docs/StatCast CSV Data/S3_Data/statcast_data_2024_" in file_key:
                print(f"Fetching file: {file_key} from {STATCAST_S3_BUCKET}...")

                # Read file from S3
                s3_object = s3_client.get_object(Bucket=STATCAST_S3_BUCKET, Key=file_key)
                csv_data = s3_object["Body"].read().decode("utf-8")

                # Convert to DataFrame
                df = pd.read_csv(StringIO(csv_data))

                # Filter only relevant game data
                df = df[(df["game_date"] == game_date) & (df["batter_id"] == batter_id)]

                if not df.empty:
                    statcast_data.append(df)

    except Exception as e:
        print(f"Error retrieving data from S3: {e}")
        return pd.DataFrame()

    # Combine all months into a single DataFrame
    return pd.concat(statcast_data, ignore_index=True) if statcast_data else pd.DataFrame()


# Load Statcast Data from S3
statcast_data = load_statcast_data_from_s3()

if not statcast_data.empty:
    print(f"Loaded {len(statcast_data)} rows for game_date {game_date} & batter_id {batter_id}.")
else:
    print(f"No statcast data found for game_date {game_date} & batter_id {batter_id}.")
    exit()

### Retrieve `home_team` and `away_team` Using `game_id`**
sample_game_ids = statcast_data["game_id"].unique()  # Get unique game_ids

game_info_list = []
for game_id in sample_game_ids:
    try:
        print(f" Fetching game data for game_id: {game_id}...")
        game_data = statcast_single_game(game_id)
        game_data["game_id"] = game_id  # Manually add game_id

        # Select only relevant columns
        if "home_team" in game_data.columns and "away_team" in game_data.columns:
            game_info = game_data[["game_id", "home_team", "away_team"]].drop_duplicates()
            game_info_list.append(game_info)
        else:
            print(f" Warning: home_team/away_team missing for game {game_id}")
    except Exception as e:
        print(f" Error fetching data for game {game_id}: {e}")

# Combine all fetched game information
if game_info_list:
    game_info_df = pd.concat(game_info_list, ignore_index=True)
else:
    game_info_df = pd.DataFrame(columns=["game_id", "home_team", "away_team"])

# Merge `home_team` and `away_team` into `statcast_data`
statcast_data = statcast_data.merge(game_info_df, on="game_id", how="left")

### Fetch Full Team Names From SQL Database**
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # SQL query to get team names
    team_query = """SELECT abbreviation_games, team_name FROM teams"""
    cursor.execute(team_query)
    columns = [desc[0] for desc in cursor.description]
    team_info = pd.DataFrame(cursor.fetchall(), columns=columns)

    # SQL query to get player name based on `batter_id`
    player_query = f"""
        Select "First_Name" || ' ' || "Last_Name" AS player_name FROM players
        WHERE "key_mlbam" = '{batter_id}'
    """
    cursor.execute(player_query)
    player_name = cursor.fetchone()

    cursor.close()
    conn.close()

    # Handle case where player is not found
    if player_name:
        player_name = player_name[0]  # Extract string from tuple
    else:
        player_name = f"Player {batter_id}"  # Fallback

    print(f" Team info fetched. Shape: {team_info.shape}")
    print(f" Player name: {player_name}")

except Exception as e:
    print(f" Error fetching team or player information: {e}")
    team_info = pd.DataFrame()  # Ensure script continues even if fetching fails
    player_name = f"Player {batter_id}"  # Fallback if query fails

###  Merge `home_team` with Full Team Names**
# Check if 'home_team' exists before merging
if 'home_team' in statcast_data.columns and 'abbreviation_games' in team_info.columns:
    statcast_data = statcast_data.merge(team_info, left_on="home_team", right_on="abbreviation_games", how="left")
    statcast_data.drop(columns=["abbreviation_games"], inplace=True)  # Drop abbreviation column
else:
    print(" Skipping merge due to missing columns.")

# Confirm merge worked
print(statcast_data[["game_id", "home_team", "team_name"]].drop_duplicates().head())

### Generate Spray Chart for the Hitter**
if not statcast_data.empty:
    stadium_name = statcast_data["team_name"].iloc[0]  # Using full team name for spray chart

    # Generate Spray Chart with Dynamic Legend
    spraychart_final(statcast_data, stadium_name, title=f"Spray Chart - {game_date} - {player_name}", legend_title='Outcome')

    plt.show()  # Ensure the figure is displayed
else:
    print(f" No data found for batter {batter_id} on {game_date}.")
