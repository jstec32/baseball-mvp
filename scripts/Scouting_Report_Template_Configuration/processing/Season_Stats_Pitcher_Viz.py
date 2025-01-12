import pandas as pd
import matplotlib.pyplot as plt
import psycopg2
from scripts.Database_Configuration.visualization_config import  apply_global_styles

# Database configuration
DB_CONFIG = {
    "host": "aws-0-us-east-2.pooler.supabase.com",
    "database": "postgres",
    "user": "postgres.chcovbrcpmlxyauansqe",
    "password": "1Z4IO6fxxYw8PgxL",  # Replace with your Supabase password
    "port": 5432  # Default PostgreSQL port
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

    # Use the player's name in the title
    ax.set_title(f"Season stats for: {player_name}", fontsize=16)

    return fig


def generate_season_stats_viz(key_mlbam):
    season_stats_data = fetch_season_stats(key_mlbam)
    if season_stats_data is None or season_stats_data.empty:
        print(f"No season stats available for key_mlbam: {key_mlbam}")
        return None
    fig = visualize_season_stats_table(season_stats_data, key_mlbam)
    return fig