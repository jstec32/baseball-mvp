import boto3
import pandas as pd
import os
from io import StringIO

import requests
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Pitcher_Heatmap_Data import get_db_connection

# Load environment variables for AWS credentials (Ensure these are set)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = "baseball-data-mvp"
MLB_GAME_DATA_PATH = "mlb_game_data/mlb_game_data.csv"  # Adjust path if needed


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

        # Ensure at least one game match exists
        if game_data_filtered.empty:
            print(f"⚠ No game data found for game_id: {game_id}")
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

    query = f"""
    SELECT 
    players."First_Name" || ' ' || players."Last_Name" AS batter_name,
    inning, 
    inning_topbot, 
    pitch_type, 
    delta_run_exp::NUMERIC AS leverage_value, 
    ABS(delta_run_exp::NUMERIC) AS leverage_impact, 
    events,
    launch_angle,
    hit_distance_sc, 
    launch_speed
    FROM pitch_data
    JOIN players ON pitch_data.batter_id = players.key_mlbam
    WHERE game_id = '{game_id}'
    ORDER BY leverage_impact DESC
    LIMIT 5;
    """

    connection = get_db_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        df = pd.DataFrame(results, columns=columns)

        # Fetch and add player IDs
        df["player_id"] = df["batter_name"].apply(lambda name: fetch_player_id(name, game_id, mlb_game_data))

        return df

    except Exception as e:
        print(f" Error fetching critical moments: {e}")
        return None

    finally:
        connection.close()

import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image

import matplotlib.pyplot as plt
import pandas as pd
import requests
from io import BytesIO
from PIL import Image

import matplotlib.pyplot as plt
import pandas as pd

import matplotlib.pyplot as plt
import pandas as pd


def visualize_critical_moments_table(data, game_id, return_fig=False):
    """Create a visually enhanced table for Critical Moments."""

    # Step 1: Drop unnecessary columns (remove 'player_id')
    data = data.drop(columns=["player_id"], errors="ignore")

    # Step 2: Convert 'inning' column to an integer (remove decimal places)
    if "inning" in data.columns:
        data["inning"] = data["inning"].astype(int)

    # Step 3: Rename and add new columns
    if "hit_distance_sc" in data.columns:
        data = data.rename(columns={"hit_distance_sc": "Hit Distance"})
    if "launch_angle" in data.columns:
        data["launch_angle"] = data["launch_angle"].round(1)  # Round launch angle to 1 decimal place

    # Step 4: Format leverage values
    if "leverage_impact" in data.columns:
        data = data.drop(columns=["leverage_impact"], errors="ignore")
    if "leverage_value" in data.columns:
        data["leverage_value"] = data["leverage_value"].round(2)

    # Step 5: Setup figure
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis("off")  # Remove x and y axis

    # Step 6: Modify column headers for aesthetics
    col_labels = data.columns.tolist()
    col_labels = [col.replace("_", " ").title() for col in col_labels]  # Format column names

    # Step 7: Create Table
    table = ax.table(
        cellText=data.values,
        colLabels=col_labels,
        cellLoc="center",
        loc="center"
    )

    # Step 8: Increase row height & font size for better readability
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 2.0)  # Adjust row height to improve readability

    # Step 9: Header formatting (remove all borders except bottom)
    for col_index in range(len(col_labels)):
        table[0, col_index].set_facecolor("#404040")  # Dark gray header
        table[0, col_index].set_text_props(color="white", fontweight="bold", fontsize=12)
        table[0, col_index].set_edgecolor("black")  # Only bottom border
        table[0, col_index].set_linewidth(1.5)

    # Step 10: Remove row borders and apply alternate row background colors
    for row_index in range(1, len(data) + 1):
        for col_index in range(len(col_labels)):
            table[row_index, col_index].set_edgecolor("white")  # Remove row borders
        if row_index % 2 == 1:  # Apply alternating row color
            for col_index in range(len(col_labels)):
                table[row_index, col_index].set_facecolor("#f2f2f2")

    # Step 11: Color-code leverage impact
    leverage_column = "Leverage Value"  # Updated to match formatted headers
    leverage_col_index = col_labels.index(leverage_column)
    for row_index in range(1, len(data) + 1):
        leverage_value = float(data.iloc[row_index - 1]["leverage_value"])
        color = "#ff4d4d" if leverage_value < 0 else "#4CAF50"
        table[row_index, leverage_col_index].set_facecolor(color)
        table[row_index, leverage_col_index].set_text_props(color="white", fontweight="bold")

    # Step 12: Adjust column width for better readability
    table.auto_set_column_width(list(range(len(col_labels))))
    plt.subplots_adjust(left=0.1, right=0.9, top=0.85, bottom=0.2)

    # Return or show figure
    if return_fig:
        return fig
    else:
        plt.show()


def generate_critical_moments_visual(game_id, mlb_game_data):


    # Fetch critical moments data
    critical_moments_table = fetch_critical_moments(game_id, mlb_game_data)

    if critical_moments_table is None or critical_moments_table.empty:
        print(f" No critical moments found for game {game_id}")
        return None

    print(f" Fetched critical moments for game {game_id}")

    # Generate the table visualization
    fig = visualize_critical_moments_table(critical_moments_table, game_id, return_fig=True)

    plt.show()
    return {"critical_moments_fig": fig}


mlb_game_data = read_mlb_game_data_from_s3()
generate_critical_moments_visual("746196", mlb_game_data)