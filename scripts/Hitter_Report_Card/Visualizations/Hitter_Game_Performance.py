import os
import boto3
import pandas as pd
import matplotlib.pyplot as plt
import psycopg2
from dotenv import load_dotenv
from matplotlib import patches


def fetch_player_name(player_id):
    query = """
    SELECT CONCAT("First_Name", ' ', "Last_Name") AS player_name
    FROM players
    WHERE key_mlbam = %s;
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query, (player_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error fetching player name: {e}")
        return None

# Load .env.local file for AWS and DB credentials
load_dotenv()

# S3 Configuration
S3_BUCKET = "baseball-data-mvp"  # Set your bucket name here
S3_KEY = "mlb_game_data/box_scores_2025.csv"

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT", 5432)
}

TEAM_COLORS = {
    "Chicago White Sox": "#27251F",
    "Detroit Tigers": "#0C2340",
    "Kansas City Royals": "#004687",
    "Minnesota Twins": "#002B5C",
    "Cleveland Guardians": "#0C2340",  # Update this if needed to Guardians
    "Baltimore Orioles": "#DF4601",
    "Boston Red Sox": "#BD3039",
    "New York Yankees": "#003087",
    "Tampa Bay Rays": "#092C5C",
    "Toronto Blue Jays": "#134A8E",
    "Houston Astros": "#002D62",
    "Los Angeles Angels": "#BA0021",
    "Oakland Athletics": "#003831",
    "Seattle Mariners": "#0C2C56",
    "Texas Rangers": "#003278",
    "Chicago Cubs": "#0E3386",
    "Cincinnati Reds": "#C6011F",
    "Milwaukee Brewers": "#FFC52F",
    "Pittsburgh Pirates": "#27251F",
    "St. Louis Cardinals": "#C41E3A",
    "Atlanta Braves": "#CE1141",
    "Miami Marlins": "#00A3E0",
    "New York Mets": "#002D72",
    "Philadelphia Phillies": "#E81828",
    "Washington Nationals": "#AB0003",
    "Arizona Diamondbacks": "#A71930",
    "Colorado Rockies": "#33006F",
    "Los Angeles Dodgers": "#005A9C",
    "San Diego Padres": "#2F241D",
    "San Francisco Giants": "#FD5A1E"
}


# Function to fetch `RE_Added` from pitch_data
def fetch_re_added(game_pk, player_id):
    query = """
    SELECT COALESCE(SUM(delta_run_exp::NUMERIC), 0) AS re_added
    FROM pitch_data
    WHERE game_id = %s AND batter_id = %s
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute(query, (game_pk, player_id))
        re_added = cursor.fetchone()[0]

        cursor.close()
        conn.close()
        return re_added

    except Exception as e:
        print(f"Error fetching RE_Added from pitch_data: {e}")
        return 0  # Default to 0 if error occurs

# Function to read box scores directly from S3
def load_box_scores_from_s3():
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    obj = s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
    box_scores = pd.read_csv(obj["Body"])

    # Parse player_id to remove 'ID' prefix
    box_scores["player_id"] = box_scores["player_id"].str.replace("ID", "", regex=False)

    return box_scores


# Function to generate the hitter performance table for a specific game and player
def generate_hitter_performance_table(player_id, game_pk):
    box_scores = load_box_scores_from_s3()

    # Filter for player and game
    player_game_data = box_scores[(box_scores["player_id"] == str(player_id)) & (box_scores["game_pk"] == int(game_pk))]

    if player_game_data.empty:
        print(f"No box score data found for player {player_id} in game {game_pk}.")
        return None

    # Columns to keep (your selected columns + player_id for safety if needed)
    selected_columns = [
         "team","atBats", "hits", "doubles", "triples", "homeRuns",
        "runs", "rbi", "strikeOuts", "baseOnBalls", "stolenBases", "caughtStealing",
        "leftOnBase"
    ]

    # Build derived columns
    player_game_data.loc[:, "XB_Hits"] = player_game_data["doubles"] + player_game_data["triples"] + player_game_data["homeRuns"]

    # Fetch `RE_Added` from pitch_data and append to dataframe
    re_added = fetch_re_added(game_pk, player_id)
    player_game_data.loc[:, "RE_Added"] = re_added

    # Final columns to show in the table
    final_columns = selected_columns + ["XB_Hits", "RE_Added"]

    # Subset the dataframe
    player_game_summary = player_game_data[final_columns].copy()

    # Format the table (uppercase, percent formatting where needed, clean visuals)
    player_game_summary.columns = [col.upper() for col in player_game_summary.columns]
    print(player_game_summary.columns)

    column_remap = {
        "ATBATS": "AB",
        "HITS": "H",
        "DOUBLES": "2B",
        "TRIPLES": "3B",
        "HOMERUNS": "HR",
        "RUNS": "R",
        "RBI": "RBI",
        "STRIKEOUTS": "SO",
        "BASEONBALLS": "BB",
        "STOLENBASES": "SB",
        "CAUGHTSTEALING": "CS",
        "LEFTONBASE": "LOB",
        "XB_HITS": "XB_HITS",  # This is already correct
        "RE_ADDED": "RE_ADDED"  # Already correct
    }
    player_game_summary = player_game_summary.rename(columns=column_remap)
    return player_game_summary


def visualize_hitter_game_performance_table(player_game_summary: pd.DataFrame, hitter_name: str, return_fig=False):

    # Ensure columns are uppercase for visual consistency
    player_game_summary.columns = [col.upper() for col in player_game_summary.columns]

    # Dynamically determine the columns to display based on data provided
    columns_to_display = [
        "TEAM","AB", "R", "H", "HR", "RBI", "BB", "SO", "XB_HITS", "RE_ADDED"
    ]

    # Ensure we only display columns that actually exist in the data
    columns_to_display = [col for col in columns_to_display if col in player_game_summary.columns]
    player_game_data = player_game_summary[columns_to_display]
    # Convert RE_Added to 2 decimal places for consistency
    if "RE_ADDED" in player_game_data.columns:
        player_game_data["RE_ADDED"] = player_game_data["RE_ADDED"].round(3)

    # Fetch team name directly from data (assuming only 1 team in filtered DataFrame)
    team_name = player_game_data['TEAM'].iloc[0]  # Make sure 'TEAM' is passed through correctly
    player_game_data = player_game_data.drop('TEAM', axis=1)
    # Set up figure and axis with dynamic width based on columns count
    fig_width = max(8, len(columns_to_display) * 1.2)  # Scale width dynamically
    fig, ax = plt.subplots(figsize=(fig_width, 0.9))  # Slightly taller to fit banner and table
    ax.axis('off')  # Hide regular plot axes




    # Create table in the center
    table = ax.table(
        cellText=player_game_data.values,
        colLabels=player_game_data.columns,
        cellLoc='center',
        bbox=[0, 0, 1, 1]
    )

    # Adjust font size to fit dynamically
    table.auto_set_font_size(False)
    table.set_fontsize(12)

    for (i, j), cell in table.get_celld().items():
        cell.set_text_props(fontname="Courier")

    # Team primary color for header row
    team_color = TEAM_COLORS.get(team_name, "#333333")  # Default dark gray if team missing

    for (i, j), cell in table.get_celld().items():
        cell.set_edgecolor('lightgray')
        if i == 0:  # Header row
            cell.set_facecolor(team_color)
            cell.set_text_props(weight='bold', color='white')
        else:
            cell.set_facecolor("white")

    # Tighten layout
    plt.rcParams['pdf.fonttype'] = 42  # TrueType
    plt.rcParams['ps.fonttype'] = 42
    if return_fig:
        return fig
    else:
        plt.show()


def generate_hitter_game_performance_visual(player_id, game_pk):

    # Generate the player game table using your existing working function
    player_game_table = generate_hitter_performance_table(player_id, game_pk)

    if player_game_table is None or player_game_table.empty:
        print(f" No game performance data found for player {player_id} in game {game_pk}.")
        return None

    # Extract player name (this is optional if you want it in the title)
    player_name = fetch_player_name(player_id)

    if not player_name:
        player_name = "Unknown Player"

    # Generate and return the visualization
    fig = visualize_hitter_game_performance_table(player_game_table, player_name, return_fig=True)


    return fig



