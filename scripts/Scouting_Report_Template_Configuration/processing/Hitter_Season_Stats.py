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
    hs.season,
    hs.batting_average AS ba,
    hs.ops,
    hs.ld_percent,
    hs.gb_percent,
    hs.fb_percent,
    hs.bb_percent,
    hs.k_percent
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

# Visualize most recent hitter stats as a table
def visualize_recent_hitter_stats_table(data, hitter_name, return_fig=False):
    apply_global_styles()

    # Format percentages
    percentage_columns = ["ld_percent", "gb_percent", "fb_percent", "bb_percent", "k_percent"]
    for column in percentage_columns:
        if column in data.columns:
            data[column] = (data[column] * 100).round(2)

    # Create the figure
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.axis('off')

    # Create the table
    table = ax.table(
        cellText=data.values,
        colLabels=data.columns,
        cellLoc='center',
        loc='center'
    )

    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(col=list(range(len(data.columns))))

    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    ax.set_title(f"Season Stats for  (ID: {hitter_name})", fontsize=16)

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

    return {"hitter_stats_fig": fig}





