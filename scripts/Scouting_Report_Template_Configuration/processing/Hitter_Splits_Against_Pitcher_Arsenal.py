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

# Exact SQL query with placeholders
SQL_QUERY_TEMPLATE = """
WITH pitcher_arsenal AS (
    SELECT DISTINCT pitch_type
    FROM pitch_data
    WHERE pitcher_id = '{pitcher_id}'
),
hitter_performance AS (
    SELECT 
        pd.pitch_type,
        COUNT(*) AS total_pitches,
        SUM(CASE WHEN pd.description = 'hit_into_play' THEN 1 ELSE 0 END) AS total_batted_balls,
        SUM(CASE WHEN pd.launch_speed >= 95 AND pd.description = 'hit_into_play' THEN 1 ELSE 0 END) AS hard_hit_balls,
        SUM(CASE WHEN pd.description LIKE 'swing%' OR pd.description = 'hit_into_play' THEN 1 ELSE 0 END) AS total_swings,
        SUM(CASE WHEN pd.description = 'swinging_strike' THEN 1 ELSE 0 END) AS total_whiffs,
        SUM(CASE WHEN pd.events = 'single' THEN 1 ELSE 0 END) AS singles,
        SUM(CASE WHEN pd.events = 'double' THEN 1 ELSE 0 END) AS doubles,
        SUM(CASE WHEN pd.events = 'triple' THEN 1 ELSE 0 END) AS triples,
        SUM(CASE WHEN pd.events = 'home_run' THEN 1 ELSE 0 END) AS home_runs,
        SUM(CASE WHEN pd.events IN ('single', 'double', 'triple', 'home_run') THEN 1 ELSE 0 END) AS total_hits,
        SUM(CASE WHEN pd.events NOT IN ('walk', 'hit_by_pitch', 'sac_fly') THEN 1 ELSE 0 END) AS at_bats
    FROM pitch_data pd
    JOIN pitcher_arsenal pa ON pd.pitch_type = pa.pitch_type
    WHERE pd.batter_id = '{hitter_id}'
    GROUP BY pd.pitch_type
)
SELECT 
    hp.pitch_type,
    ROUND(hp.hard_hit_balls * 100.0 / NULLIF(hp.total_batted_balls, 0), 2) AS hard_hit_rate_percent,
    ROUND(hp.total_whiffs * 100.0 / NULLIF(hp.total_swings, 0), 2) AS whiff_rate_percent,
    ROUND((hp.singles + (2 * hp.doubles) + (3 * hp.triples) + (4 * hp.home_runs)) * 1.0 / NULLIF(hp.at_bats, 0), 3) AS slugging_percentage
FROM hitter_performance hp
ORDER BY hp.pitch_type;
"""

# Fetch data from the database
def fetch_hitter_splits(pitcher_id, hitter_id):
    try:
        # Replace placeholders dynamically
        query = SQL_QUERY_TEMPLATE.format(pitcher_id=pitcher_id, hitter_id=hitter_id)

        # Connect to the database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Execute the query
        cursor.execute(query)
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

# Generate a table visualization
def plot_hitter_splits_table(data, hitter_id, return_fig=False):

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

    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(col=list(range(len(data.columns))))

    ax.set_title(f"Splits against pitcher's arsenal", fontsize=16)


    if return_fig:
        return fig
    else:
        plt.show()


# Main function for manual testing
def generate_hitter_splits_visual(pitcher_id, hitter_id):
    apply_global_styles()
    # Fetch the data
    hitter_splits_data = fetch_hitter_splits(pitcher_id, hitter_id)

    if hitter_splits_data is None or hitter_splits_data.empty:
        print(f"No hitter splits data available for pitcher_id: {pitcher_id} and hitter_id: {hitter_id}")
        return None

    print(f"Fetched {len(hitter_splits_data)} rows of hitter splits data for pitcher_id: {pitcher_id} and hitter_id: {hitter_id}")

    # Generate table figure
    fig = plot_hitter_splits_table(hitter_splits_data, hitter_id, return_fig=True)

    return {"hitter_splits_table": fig}




