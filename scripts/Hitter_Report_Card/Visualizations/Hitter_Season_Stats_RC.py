import pandas as pd
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

# SQL query for the most recent season stats
SQL_QUERY = """
WITH players_with_team AS (
    SELECT 
        p.*, 
        t.abbreviation_games
    FROM players p
    JOIN teams t
        ON p."teamID" = t.abbreviation_players
),
most_recent_season AS (
    SELECT MAX(hs.season) AS season
    FROM hitter_season_statistics hs
    JOIN players_with_team pwt
        ON CONCAT(pwt."First_Name", ' ', pwt."Last_Name") = hs.name
    WHERE pwt.key_mlbam = %s
)
SELECT 
    hs.batting_average AS BA,
    hs.on_base_percentage AS OBP,
    hs.slugging_percentage AS SLG,
    hs.ops AS OPS,
    hs.wrc_plus AS WRC,
    hs.home_runs AS HRs,
    hs.rbi AS RBI,
    hs.hard_hit_percent AS HHR,
    hs.k_percent AS KR,
    hs.bb_percent AS BBR
FROM hitter_season_statistics hs
JOIN players_with_team pwt
    ON CONCAT(pwt."First_Name", ' ', pwt."Last_Name") = hs.name
JOIN most_recent_season mrs
    ON hs.season = mrs.season
WHERE pwt.key_mlbam = %s;
"""

# SQL query to fetch the hitter's name
NAME_QUERY = """
SELECT CONCAT(p."First_Name", ' ', p."Last_Name") AS hitter_name
FROM players p
WHERE p.key_mlbam = %s;
"""

# Fetch most recent hitter stats
def fetch_recent_hitter_stats_and_name(key_mlbam):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Fetch the hitter's stats
        cursor.execute(SQL_QUERY, (key_mlbam, key_mlbam))
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()

        # Fetch the hitter's name
        cursor.execute(NAME_QUERY, (key_mlbam,))
        hitter_name = cursor.fetchone()[0]

        # Close connection
        cursor.close()
        conn.close()

        # Convert stats to a DataFrame
        stats_df = pd.DataFrame(data, columns=columns)

        return stats_df, hitter_name

    except Exception as e:
        print(f"Error fetching data: {e}")
        return None, None

# Visualize most recent hitter stats as a clean table
def visualize_recent_hitter_stats_table(data, hitter_name, color_dict=None, table_width=12, max_rows=10, return_fig=False):
    apply_global_styles()

    # Convert percentage columns to % format (only those with "R" in the name)
    percentage_columns = [col for col in data.columns if col.endswith("r")]  # Detect columns with 'R'
    for column in percentage_columns:
        if column in data.columns:
            data[column] = (data[column] * 100).round(2).astype(str) + '%'  # Convert to string with %
    print(data)
    # Ensure OPS is rounded to three decimal places
    if "ops" in data.columns:
        data["ops"] = data["ops"].round(3)

    # Convert column names to uppercase
    data.columns = [col.upper() for col in data.columns]
    data.columns = [col[:-1] + "%" if col.endswith("R") else col for col in data.columns]

    # Increase table size for better visibility
    fig, ax = plt.subplots(figsize=(10, 2))

    ax.axis('off')  # Remove axes

    # Create the table
    table = ax.table(
        cellText=data.values,
        colLabels=data.columns,
        cellLoc='center',
        loc='center'
    )

    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(12)  # Increase font size for readability
    table.auto_set_column_width(col=list(range(len(data.columns))))

    # Remove all table borders first
    for key, cell in table.get_celld().items():
        cell.set_linewidth(0)  # Remove all borders

    # Add a bottom border ONLY for the column headers
    header_row_index = 0  # The row index for headers
    for col_index in range(len(data.columns)):
        table[header_row_index, col_index].visible_edges = "B"  # Only add bottom border
        table[header_row_index, col_index].set_linewidth(2)  # Adjust line thickness
        table[header_row_index, col_index].set_edgecolor("black")  # Black border

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    if return_fig:
        return fig
    else:
        plt.show()




# Main function for testing
def generate_hitter_season_stats_visual(key_mlbam):

    # Fetch hitter stats and name
    recent_hitter_stats, hitter_name = fetch_recent_hitter_stats_and_name(key_mlbam)

    if recent_hitter_stats is None or recent_hitter_stats.empty or hitter_name is None:
        print(f"Failed to fetch data for hitter ID: {key_mlbam}")
        return None

    print(f"Fetched stats for {hitter_name}.")

    # Generate the table visualization
    fig = visualize_recent_hitter_stats_table(recent_hitter_stats, hitter_name, return_fig=True)
    plt.show()
    return {"hitter_stats_fig": fig}

generate_hitter_season_stats_visual("621566")



