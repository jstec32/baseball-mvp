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


def generate_spray_chart_visual(batter_id, game_date):


    # Step 1: Fetch Statcast data from the database
    query = """
    SELECT game_id, game_date, batter_id, hc_x, hc_y, hit_distance_sc, events
    FROM pitch_data
    WHERE batter_id = %s AND game_date = %s;
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        statcast_data = pd.read_sql(query, conn, params=(batter_id, game_date))
        conn.close()

        if statcast_data.empty:
            print(f" No Statcast data found for batter_id={batter_id} on game_date={game_date}.")
            return None
        print(f" Fetched {len(statcast_data)} rows for batter_id={batter_id} on game_date={game_date}")

    except Exception as e:
        print(f" Error fetching Statcast data from database: {e}")
        return None

    # Step 2: Fetch game information (home & away team)
    sample_game_ids = statcast_data["game_id"].unique()
    game_info_list = []

    for game_id in sample_game_ids:
        try:
            game_data = statcast_single_game(game_id)
            game_data["game_id"] = game_id  # Manually add game_id

            if "home_team" in game_data.columns and "away_team" in game_data.columns:
                game_info = game_data[["game_id", "home_team", "away_team"]].drop_duplicates()
                game_info_list.append(game_info)
            else:
                print(f"⚠ Warning: home_team/away_team missing for game {game_id}")

        except Exception as e:
            print(f" Error fetching data for game {game_id}: {e}")

    if game_info_list:
        game_info_df = pd.concat(game_info_list, ignore_index=True)
    else:
        game_info_df = pd.DataFrame(columns=["game_id", "home_team", "away_team"])

    # Merge `home_team` and `away_team` into `statcast_data`
    statcast_data = statcast_data.merge(game_info_df, on="game_id", how="left")

    # Step 3: Fetch Full Team Names from SQL Database
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Get team names
        team_query = """SELECT abbreviation_games, team_name FROM teams"""
        cursor.execute(team_query)
        columns = [desc[0] for desc in cursor.description]
        team_info = pd.DataFrame(cursor.fetchall(), columns=columns)

        # Get player name from database
        player_query = f"""
            SELECT "First_Name" || ' ' || "Last_Name" AS player_name FROM players
            WHERE "key_mlbam" = '{batter_id}'
        """
        cursor.execute(player_query)
        player_name = cursor.fetchone()

        cursor.close()
        conn.close()

        player_name = player_name[0] if player_name else f"Player {batter_id}"

        print(f" Team info fetched. Shape: {team_info.shape}")
        print(f" Player name: {player_name}")

    except Exception as e:
        print(f" Error fetching team or player information: {e}")
        team_info = pd.DataFrame()  # Ensure script continues even if fetching fails
        player_name = f"Player {batter_id}"

    # Step 4: Merge team name with statcast_data
    if 'home_team' in statcast_data.columns and 'abbreviation_games' in team_info.columns:
        statcast_data = statcast_data.merge(team_info, left_on="home_team", right_on="abbreviation_games", how="left")
        statcast_data.drop(columns=["abbreviation_games"], inplace=True)
    else:
        print(" Skipping merge due to missing columns.")

    # Confirm merge worked

    # Step 5: Generate Spray Chart
    if not statcast_data.empty:
        stadium_name = statcast_data["team_name"].iloc[0]  # Using full team name for spray chart

        fig = spraychart_final(statcast_data, stadium_name, title=f"",
                               legend_title='Outcome')
        print(f" Spray chart generated for {player_name}.")
        return fig  # Returning the figure for PDF integration
    else:
        print(f" No data found for batter {batter_id} on {game_date}.")
        return None



