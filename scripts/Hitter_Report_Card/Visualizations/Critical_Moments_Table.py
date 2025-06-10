import boto3
import pandas as pd
import os
from io import StringIO
import requests
from io import BytesIO
from PIL import Image
import matplotlib.pyplot as plt
import pandas as pd
import requests
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Pitcher_Heatmap_Data import get_db_connection

# Load environment variables for AWS credentials (Ensure these are set)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = "baseball-data-mvp"
MLB_GAME_DATA_PATH = "mlb_game_data/mlb_game_data_2025.csv"  # Adjust path if needed

TEAM_COLORS = {
    "Chicago White Sox": "#27251F",
    "Detroit Tigers": "#0C2340",
    "Kansas City Royals": "#004687",
    "Minnesota Twins": "#002B5C",
    "Cleveland Guardians": "#0C2340",
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


def read_mlb_game_data_from_s3():

    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )

        # Fetch CSV from S3
        response = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=MLB_GAME_DATA_PATH)
        csv_content = response['Body'].read().decode('utf-8')

        # Read into DataFrame
        mlb_game_data = pd.read_csv(StringIO(csv_content))
        print(f" Loaded {len(mlb_game_data)} game records from S3.")

        return mlb_game_data

    except Exception as e:
        print(f" Error fetching MLB game data from S3: {e}")
        return None

def fetch_player_id(batter_name, game_id, mlb_game_data):

    try:
        # Filter the game data for the specific game_id
        game_data_filtered = mlb_game_data[mlb_game_data["game_id"] == int(game_id)]
        print(batter_name)
        print(game_id)
        # Ensure at least one game match exists
        if game_data_filtered.empty:
            print(f" No game data found for game_id: {game_id}")
            return None

        # Fetch player ID from the database using name + game_id
        query = """
        SELECT key_mlbam FROM players
        WHERE CONCAT("First_Name", ' ', "Last_Name") = %s
        AND key_mlbam IN (
            SELECT batter_id FROM pitch_data WHERE game_id = %s
        );
        """

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, (batter_name, game_id))
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        if not results:
            print(f" No player ID found for {batter_name} in game {game_id}.")
            return None

        if len(results) == 1:
            return results[0][0]  # Return single match

        print(f" Multiple players found for {batter_name} in game {game_id}. Returning first match.")
        return results[0][0]  # Return first match if duplicates exist

    except Exception as e:
        print(f" Error fetching player ID: {e}")
        return None

def fetch_player_headshot(hitter_id):

    try:
        url = f'https://img.mlbstatic.com/mlb-photos/image/upload/w_213,d_people:generic:headshot:silo:current.png,q_auto:best,f_auto/v1/people/{hitter_id}/headshot/67/current'
        response = requests.get(url)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
        else:
            print(f"Failed to fetch headshot for hitter ID: {hitter_id} (status code: {response.status_code})")
            return None
    except Exception as e:
        print(f"Error fetching headshot for hitter ID {hitter_id}: {e}")
        return None

def fetch_critical_moments(game_id, mlb_game_data):
    query = """
        WITH player_with_team AS (
    SELECT 
        p.key_mlbam,
        CONCAT(p."First_Name", ' ', p."Last_Name") AS player_name,
        t.name AS team_name
    FROM players p
    JOIN teams t
        ON p."teamID" = t.abbreviation_players
)
SELECT 
    pwt.player_name AS batter_name,
    pwt.team_name,
    inning, 
    inning_topbot, 
    pitch_type, 
    CASE 
        WHEN pd.delta_run_exp ~ '^[-+]?[0-9]*\.?[0-9]+$' 
        THEN pd.delta_run_exp::NUMERIC 
        ELSE NULL 
    END AS leverage_value,
    CASE 
        WHEN pd.delta_run_exp ~ '^[-+]?[0-9]*\.?[0-9]+$' 
        THEN ABS(pd.delta_run_exp::NUMERIC) 
        ELSE NULL 
    END AS leverage_impact,
    events,
    launch_angle,
    hit_distance_sc, 
    launch_speed
FROM pitch_data pd
JOIN player_with_team pwt
    ON pd.batter_id = pwt.key_mlbam
WHERE pd.game_id = %s
ORDER BY leverage_impact DESC
LIMIT 5;"""

    connection = get_db_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute(query, (game_id,))
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(results, columns=columns)

        if df.empty:
            print(f" No critical moments found for game {game_id}")
            return None

        df["leverage_value"] = pd.to_numeric(df["leverage_value"], errors="coerce")
        valid_rows = df[df["leverage_value"].notnull()]

        # Fallback logic if fewer than 5
        if len(valid_rows) < 5:
            fallback_query = query.replace("LIMIT 5", "LIMIT 15")
            cursor.execute(fallback_query, (game_id,))
            fallback_results = cursor.fetchall()
            fallback_df = pd.DataFrame(fallback_results, columns=columns)

            fallback_df["leverage_value"] = pd.to_numeric(fallback_df["leverage_value"], errors="coerce")

            # Combine and drop blanks explicitly
            combined_df = pd.concat([valid_rows, fallback_df], ignore_index=True)
            combined_df = combined_df[combined_df["leverage_value"].notnull()]
            combined_df = combined_df.drop_duplicates().head(5)
            valid_rows = combined_df

        # Add player_id column
        valid_rows["player_id"] = valid_rows["batter_name"].apply(
            lambda name: fetch_player_id(name, game_id, mlb_game_data)
        )

        return valid_rows.reset_index(drop=True)

    except Exception as e:
        print(f" Error fetching critical moments: {e}")
        return None

    finally:
        connection.close()



def visualize_critical_moments_table(data, team_name, game_id, return_fig=False):
    if {"inning", "inning_topbot"}.issubset(data.columns):
        data["Inning"] = data["inning_topbot"].str.title() + " " + data["inning"].astype(int).astype(str)
        data.drop(columns=["inning", "inning_topbot"], inplace=True)

    # Format columns
    if "launch_angle" in data.columns:
        data["launch_angle"] = data["launch_angle"].round(1)
    if "events" in data.columns:
        data["events"] = data["events"].str.replace("_", " ").str.title()

    # Drop not needed columns
    data.drop(columns=["player_id", "team_name", "leverage_impact"], errors="ignore", inplace=True)
    data.fillna("", inplace=True)

    header_renames = {
        "batter_name": "Batter",
        "Inning": "Inning",
        "pitch_type": "Pitch",
        "leverage_value": "Leverage",
        "events": "Event",
        "launch_angle": "LA",
        "hit_distance_sc": "Distance",
        "launch_speed": "Exit Velo"
    }

    col_labels = data.columns.tolist()

    def smart_title(text):
        return text if text.isupper() else text.title()

    col_labels = [smart_title(header_renames.get(col, col)) for col in col_labels]

    # Set up figure for report
    fig, ax = plt.subplots(figsize=(10, 2.5))  # Keep height smaller than before to fit report card
    ax.axis("off")

    # Create Table
    table = ax.table(
        cellText=data.values,
        colLabels=col_labels,
        cellLoc="center",
        bbox=[0, 0, 1, 1]
    )

    # Increase font size
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.0, 1.5)

    for (i, j), cell in table.get_celld().items():
        cell.set_text_props(fontname="Courier")


    team_color = TEAM_COLORS.get(team_name, "#333333")  # Fallback to dark gray if missing

    for col_index in range(len(col_labels)):
        table[0, col_index].set_facecolor(team_color)  # Use team color
        table[0, col_index].set_text_props(color="white", fontweight="bold", fontsize=12)
        table[0, col_index].set_edgecolor("white")  # Remove top/side borders


    for row_index in range(1, len(data) + 1):
        for col_index in range(len(col_labels)):
            table[row_index, col_index].set_edgecolor("white")  # Remove row borders
        if row_index % 2 == 1:  # Apply alternating row color
            for col_index in range(len(col_labels)):
                table[row_index, col_index].set_facecolor("#f2f2f2")

    # Color-code leverage column
    data["leverage_value"] = pd.to_numeric(data["leverage_value"], errors="coerce").fillna(0).round(2)
    leverage_column = "Leverage"
    leverage_col_index = col_labels.index(leverage_column)
    for row_index in range(1, len(data) + 1):
        leverage_value = float(data.iloc[row_index - 1]["leverage_value"])
        color = "#ff4d4d" if leverage_value < 0 else "#4CAF50"
        table[row_index, leverage_col_index].set_facecolor(color)
        table[row_index, leverage_col_index].set_text_props(color="white", fontweight="bold")
    table.auto_set_column_width(list(range(len(col_labels))))


    if return_fig:
        return fig
    else:
        plt.show()


def generate_critical_moments_visual(game_id):

    AWS_BUCKET_NAME = "baseball-data-mvp"
    MLB_GAME_DATA_PATH = "mlb_game_data/mlb_game_data.csv"
    # Load from S3
    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

        response = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=MLB_GAME_DATA_PATH)
        csv_content = response['Body'].read().decode('utf-8')

        # Read DF
        mlb_game_data = pd.read_csv(StringIO(csv_content))
        print(f" Loaded {len(mlb_game_data)} game records from S3.")
    except Exception as e:
        print(f" Error fetching MLB game data from S3: {e}")
        return None

    # Fetch critical moments
    query = """
        WITH player_with_team AS (
    SELECT 
        p.key_mlbam,
        CONCAT(p."First_Name", ' ', p."Last_Name") AS player_name,
        t.name AS team_name
    FROM players p
    JOIN teams t
        ON p."teamID" = t.abbreviation_players
)
SELECT 
    pwt.player_name AS batter_name,
    pwt.team_name,
    inning, 
    inning_topbot, 
    pitch_type, 
    CASE 
        WHEN pd.delta_run_exp ~ '^[-+]?[0-9]*\.?[0-9]+$' 
        THEN pd.delta_run_exp::NUMERIC 
        ELSE NULL 
    END AS leverage_value,
    CASE 
        WHEN pd.delta_run_exp ~ '^[-+]?[0-9]*\.?[0-9]+$' 
        THEN ABS(pd.delta_run_exp::NUMERIC) 
        ELSE NULL 
    END AS leverage_impact,
    events,
    launch_angle,
    hit_distance_sc, 
    launch_speed
FROM pitch_data pd
JOIN player_with_team pwt
    ON pd.batter_id = pwt.key_mlbam
WHERE pd.game_id = %s AND pd.delta_run_exp ~ '^[-+]?[0-9]*\\.?[0-9]+$'
ORDER BY leverage_impact DESC
LIMIT 5;
    """

    connection = get_db_connection()
    if not connection:
        print(f" Failed to establish database connection.")
        return None

    try:
        cursor = connection.cursor()
        cursor.execute(query, (game_id,))
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(results, columns=columns)

        if df.empty:
            print(f" No critical moments found for game {game_id}")
            return None

        team_name = df["team_name"].iloc[0]

    except Exception as e:
        print(f" Error fetching critical moments: {e}")
        return None
    finally:
        connection.close()

    # Generate visualization
    fig = visualize_critical_moments_table(df, team_name, game_id, return_fig=True)

    return fig

