import pandas as pd
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import psycopg2
from dotenv import load_dotenv

from scripts.Database_Configuration.visualization_config import  apply_global_styles

import os
load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432))  # Default port 5432 if not set
}

# SQL query template for season stats
SQL_QUERY_TEMPLATE = """
WITH players_with_team AS (
    SELECT 
        p.*, 
        t.abbreviation_games
    FROM players p
    JOIN teams t
        ON p."teamID" = t.abbreviation_players
)
SELECT 
    sps.season,
    sps.innings_pitched AS ip,
    sps.era,
    sps.whip,
    sps.k_percent AS k_percentage,
    sps.bb_percent AS bb_percentage,
    sps.hr_per_9,
    sps.ld_percent,
    sps.gb_percent,
    sps.flyball_percent
FROM season_pitching_statistics sps
JOIN players_with_team pwt
    ON CONCAT(pwt."First_Name", ' ', pwt."Last_Name") = sps.name
    AND pwt.abbreviation_games = sps.team
WHERE pwt.key_mlbam = %s
ORDER BY sps.season DESC;
"""

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


# Fetch data from the database
def fetch_season_stats(key_mlbam):
    try:
        # Connect to the database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Execute the query with the dynamic key_mlbam
        cursor.execute(SQL_QUERY_TEMPLATE, (key_mlbam,))
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()

        # Close connection
        cursor.close()
        conn.close()

        # Convert data to a DataFrame
        return pd.DataFrame(data, columns=columns)

    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

# Format percentages in the DataFrame
def format_percentages(data):
    percentage_columns = ["k_percentage", "bb_percentage", "ld_percent", "gb_percent", "flyball_percent"]
    for column in percentage_columns:
        if column in data.columns:
            data[column] = (data[column] * 100).round(2).astype(str) + '%'  # Convert to percentage format
    return data

# Generate a table visualization for season stats
def visualize_season_stats_table(data, key_mlbam):
    apply_global_styles()
    # Fetch the player's name using their key_mlbam
    player_name = fetch_player_name(key_mlbam)  # Ensure this function exists and works correctly

    # Handle cases where the name is unavailable
    if not player_name:
        player_name = "Unknown Player"

    highlight_columns = {}
    if "ip" in data.columns:
        highlight_columns["ip"] = data["ip"].idxmax()  # Most innings pitched
    if "era" in data.columns:
        highlight_columns["era"] = data["era"].idxmin()  # Lowest ERA
    if "whip" in data.columns:
        highlight_columns["whip"] = data["whip"].idxmin()  # Lowest WHIP
    if "k_percentage" in data.columns:
        highlight_columns["k_percentage"] = data["k_percentage"].idxmax()  # Highest K%
    if "bb_percentage" in data.columns:
        highlight_columns["bb_percentage"] = data["bb_percentage"].idxmin()  # Lowest BB%
    if "hr_per_9" in data.columns:
        highlight_columns["hr_per_9"] = data["hr_per_9"].idxmin()  # Lowest HR%

    # Special handling for ld_percent, gb_percent, fb_percent
    if all(col in data.columns for col in ["ld_percent", "gb_percent", "flyball_percent"]):
        for idx, row in data.iterrows():
            # Find the column with the lowest value in this row
            highest_col = row[["ld_percent", "gb_percent", "flyball_percent"]].idxmax()
            highlight_columns[(highest_col, idx)] = True  # Highlight the cell in this column for this row

    # Create the figure and table visualization
    fig, ax = plt.subplots(figsize=(8, len(data) * 0.6))  # Adjust height based on rows
    ax.axis('tight')
    ax.axis('off')

    # Create the table
    table = ax.table(
        cellText=data.values,
        colLabels=data.columns,
        cellLoc='center',
        loc='center'
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(col=list(range(len(data.columns))))


    # Apply highlights to the table
    for key, value in highlight_columns.items():
        if isinstance(key, tuple):
            # Handle the (column, row) tuple case
            col, idx = key
            if col in data.columns:
                col_index = list(data.columns).index(col)
                cell = table[idx + 1, col_index]  # +1 because the header row is at index 0
                cell.set_text_props(weight='bold', color='#FF0000')  # Highlight with bold and red color
        else:
            # Handle the single column case
            col = key
            idx = value
            if col in data.columns:
                col_index = list(data.columns).index(col)
                cell = table[idx + 1, col_index]  # +1 because the header row is at index 0
                cell.set_text_props(weight='bold', color='#FF0000')  # Highlight with bold and red color

    return fig


def generate_season_stats_viz(key_mlbam):
    season_stats_data = fetch_season_stats(key_mlbam)
    if season_stats_data is None or season_stats_data.empty:
        print(f"No season stats available for key_mlbam: {key_mlbam}")
        return None
    fig = visualize_season_stats_table(season_stats_data, key_mlbam)
    fig.show()
    return fig
