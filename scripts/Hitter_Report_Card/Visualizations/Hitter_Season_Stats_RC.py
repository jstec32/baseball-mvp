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

# SQL query for the most recent season stats
SQL_QUERY = """
WITH players_with_team AS (
    SELECT 
        p.*, 
        t.abbreviation_games,
        t.name AS team_name
    FROM players p
    JOIN teams t
        ON p."teamID" = t.abbreviation_players
),
most_recent_season AS (
    SELECT MAX(hs.season) AS season
    FROM hitter_season_statistics hs
    JOIN players_with_team pwt
        ON unaccent(LOWER(TRIM(CONCAT(pwt."First_Name", ' ', pwt."Last_Name")))) =
           unaccent(LOWER(TRIM(hs.name)))
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
    hs.bb_percent AS BBR,
    pwt.team_name
FROM hitter_season_statistics hs
JOIN players_with_team pwt
    ON unaccent(LOWER(TRIM(CONCAT(pwt."First_Name", ' ', pwt."Last_Name")))) =
       unaccent(LOWER(TRIM(hs.name)))
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

def fetch_hitter_stats_and_team(key_mlbam):

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Execute SQL query to fetch hitter stats
        cursor.execute(SQL_QUERY, (key_mlbam, key_mlbam))
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()

        # Fetch the hitter's name
        cursor.execute(NAME_QUERY, (key_mlbam,))
        name_result = cursor.fetchone()

        cursor.close()
        conn.close()
        print(data)
        print(key_mlbam)
        # Check if we successfully retrieved hitter data
        if not data:
            print(f" No season stats found for hitter ID: {key_mlbam}")
            return None, None, None

        # Convert results to DataFrame
        df = pd.DataFrame(data, columns=columns)

        if df.empty:
            print(f" Hitter stats DataFrame is empty after processing.")
            return None, None, None

        # Extract hitter name (Ensure a valid result exists)
        hitter_name = name_result[0] if name_result else None
        if not hitter_name:
            print(f" Hitter name not found for ID: {key_mlbam}")
            return None, None, None

        # Extract team name safely
        if "team_name" in df.columns:
            team_name = df["team_name"].iloc[0]
            df = df.drop(columns=["team_name"])  # Drop after capturing
        else:
            print(f" Team name missing in fetched data for hitter ID: {key_mlbam}")
            return None, None, None

        print(f" Successfully fetched data for {hitter_name} ({team_name}).")
        return df, hitter_name, team_name

    except Exception as e:
        print(f" Error fetching hitter data: {e}")
        return None, None, None


def visualize_recent_hitter_stats_table(data, team_name: str, hitter_name: str, return_fig=False):
    data.columns = [col.upper() for col in data.columns]

    percentage_columns = [col for col in data.columns if col.endswith("R")]
    for column in percentage_columns:
        if column in data.columns:
            data[column] = (data[column] * 100).round(2).astype(str) + '%'
    header_renames = {
        "HHR": "HH%",
        "KR": "K%",
        "BBR": "BB%",
        "HRS":"HR"
    }
    data.columns = [header_renames.get(col, col) for col in data.columns]

    if "OPS" in data.columns:
        data["OPS"] = data["OPS"].round(3)
    if "BA" in data.columns:
        data["BA"] = data["BA"].round(3)

    fig, ax = plt.subplots(figsize=(10, 0.9))
    ax.axis('off')

    table = ax.table(
        cellText=data.values,
        colLabels=data.columns,
        cellLoc='center',
        bbox=[0, 0, 1, 1]
    )

    table.auto_set_font_size(False)
    table.set_fontsize(12)

    for (i, j), cell in table.get_celld().items():
        cell.set_text_props(fontname="Courier")

    team_color = TEAM_COLORS.get(team_name, "#333333")

    for (i, j), cell in table.get_celld().items():
        cell.set_edgecolor('lightgray')
        if i == 0:
            cell.set_facecolor(team_color)
            cell.set_text_props(weight='bold', color='white')
        else:
            cell.set_facecolor("white")

    plt.rcParams['pdf.fonttype'] = 42  # TrueType
    plt.rcParams['ps.fonttype'] = 42
    if return_fig:
        return fig
    else:
        plt.show()


# Main function for testing
def generate_hitter_season_stats_visual(key_mlbam):
    stats_df, hitter_name, team_name = fetch_hitter_stats_and_team(key_mlbam)

    if stats_df is None or stats_df.empty or hitter_name is None or team_name is None:
        print(f"Failed to fetch complete data for hitter ID: {key_mlbam}")
        return None

    print(f"Fetched stats for {hitter_name} ({team_name}).")

    fig = visualize_recent_hitter_stats_table(stats_df, team_name, hitter_name, return_fig=True)
    plt.show()
    return fig, hitter_name, team_name
