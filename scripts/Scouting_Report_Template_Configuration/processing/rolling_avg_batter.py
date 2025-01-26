import pandas as pd
import matplotlib.pyplot as plt
import psycopg2
from matplotlib.ticker import FuncFormatter

from scripts.Database_Configuration.Hitter_Season_Stats import DB_CONFIG
from scripts.Database_Configuration.visualization_config import  apply_global_styles

SQL_QUERY_ROLLING_AVERAGES = """
SELECT
    game_date,
    CASE
        WHEN events IN ('single', 'double', 'triple', 'home_run') THEN 1 ELSE 0
    END AS hit,
    CASE
        WHEN events IN ('walk', 'hit_by_pitch') THEN 1 ELSE 0
    END AS on_base,
    CASE
        WHEN events IN ('single') THEN 1
        WHEN events IN ('double') THEN 2
        WHEN events IN ('triple') THEN 3
        WHEN events IN ('home_run') THEN 4 ELSE 0
    END AS total_bases,
    CASE
        WHEN events NOT IN ('walk', 'hit_by_pitch', 'sacrifice', 'catcher_interference', 'intent_walk', 'null') THEN 1 ELSE 0
    END AS at_bat
FROM pitch_data
WHERE batter_id = %s
    AND game_date >= '2024-01-01'
    AND game_date <= '2024-12-31'
ORDER BY game_date;
"""

# Fetch rolling averages data from the database
def fetch_rolling_averages_data(hitter_id):
    try:
        # Connect to the database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Execute the query with the dynamic hitter_id
        cursor.execute(SQL_QUERY_ROLLING_AVERAGES, (hitter_id,))
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()

        # Close connection
        cursor.close()
        conn.close()

        # Convert data to a DataFrame
        return pd.DataFrame(data, columns=columns)

    except Exception as e:
        print(f"Error fetching rolling averages data: {e}")
        return None

def compute_rolling_averages_from_db(hitter_id, rolling_window=15):
    # Fetch data from the database
    pitch_data = fetch_rolling_averages_data(hitter_id)

    if pitch_data is None or pitch_data.empty:
        print(f"No data available for hitter ID: {hitter_id}")
        return None

    # Convert game_date to datetime
    pitch_data['game_date'] = pd.to_datetime(pitch_data['game_date'])

    # Aggregate daily stats
    daily_stats = pitch_data.groupby('game_date').agg(
        hits=('hit', 'sum'),
        on_base=('on_base', 'sum'),
        total_bases=('total_bases', 'sum'),
        at_bats=('at_bat', 'sum')
    ).reset_index()

    # Calculate cumulative stats
    daily_stats['cumulative_hits'] = daily_stats['hits'].cumsum()
    daily_stats['cumulative_on_base'] = daily_stats['on_base'].cumsum()
    daily_stats['cumulative_total_bases'] = daily_stats['total_bases'].cumsum()
    daily_stats['cumulative_at_bats'] = daily_stats['at_bats'].cumsum()

    # Calculate metrics
    daily_stats['BA'] = daily_stats['cumulative_hits'] / daily_stats['cumulative_at_bats']
    daily_stats['OBP'] = (daily_stats['cumulative_hits'] + daily_stats['cumulative_on_base']) / (
        daily_stats['cumulative_at_bats'] + daily_stats['cumulative_on_base']
    )
    daily_stats['SLG'] = daily_stats['cumulative_total_bases'] / daily_stats['cumulative_at_bats']
    daily_stats['OPS'] = daily_stats['OBP'] + daily_stats['SLG']

    # Compute rolling averages
    daily_stats['rolling_BA'] = daily_stats['BA'].rolling(rolling_window).mean()
    daily_stats['rolling_OBP'] = daily_stats['OBP'].rolling(rolling_window).mean()
    daily_stats['rolling_SLG'] = daily_stats['SLG'].rolling(rolling_window).mean()
    daily_stats['rolling_OPS'] = daily_stats['OPS'].rolling(rolling_window).mean()

    return daily_stats

def plot_rolling_averages_from_db(daily_stats, hitter_name, return_fig=False):
    plt.figure(figsize=(12, 6))

    # Plot rolling averages
    plt.plot(daily_stats['game_date'], daily_stats['rolling_BA'], label="BA (Batting Avg)", color='blue', linewidth=2)
    plt.plot(daily_stats['game_date'], daily_stats['rolling_OBP'], label="OBP (On-Base %)", color='green', linewidth=2)
    plt.plot(daily_stats['game_date'], daily_stats['rolling_SLG'], label="SLG (Slugging %)", color='orange', linewidth=2)

    # Chart settings
    plt.title(f"Rolling Averages for {hitter_name} (2024 Season)", fontsize=16, weight='bold')
    plt.xlabel("Game Date", fontsize=12)
    plt.ylabel("Rolling Averages", fontsize=12)
    plt.legend(loc='upper left', fontsize=10)
    plt.grid(alpha=0.3)
    plt.tight_layout()

    # Set y-axis to three decimal places
    ax = plt.gca()
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f'{x:.3f}'))

    # Additional chart settings
    plt.grid(alpha=0.3)
    plt.tight_layout()

    if return_fig:
        return plt.gcf()
    else:
        plt.show()

hitter_id = '518692'  # Replace with valid hitter ID
rolling_stats = compute_rolling_averages_from_db(hitter_id)

if rolling_stats is not None:
    rolling_avg_fig = plot_rolling_averages_from_db(rolling_stats, hitter_name="Freddie Freeman", return_fig=True)
    rolling_avg_fig.show()
