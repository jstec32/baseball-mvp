import pandas as pd
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import psycopg2
from matplotlib.ticker import FuncFormatter

from scripts.Database_Configuration.Hitter_Season_Stats import DB_CONFIG
from scripts.Database_Configuration.visualization_config import  apply_global_styles
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Pitcher_Heatmap_Data import fetch_player_name

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
    AND game_date >= '2025-01-01'
    AND game_date <= '2025-12-31'
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
    daily_stats = daily_stats.sort_values("game_date").reset_index(drop=True)

    if daily_stats.empty:
        print("No daily stats found after aggregation.")
        return None

    # Avoid divide-by-zero
    daily_stats = daily_stats[daily_stats["at_bats"] > 0]

    # Compute raw per-game stats (no rolling yet)
    daily_stats['BA'] = daily_stats['hits'] / daily_stats['at_bats']
    daily_stats['OBP'] = (daily_stats['hits'] + daily_stats['on_base']) / (
        daily_stats['at_bats'] + daily_stats['on_base']
    )
    daily_stats['SLG'] = daily_stats['total_bases'] / daily_stats['at_bats']
    daily_stats['OPS'] = daily_stats['OBP'] + daily_stats['SLG']

    # If we only have one game, set rolling_* equal to raw daily stats
    if len(daily_stats) < rolling_window:
        daily_stats['rolling_BA'] = daily_stats['BA']
        daily_stats['rolling_OBP'] = daily_stats['OBP']
        daily_stats['rolling_SLG'] = daily_stats['SLG']
        daily_stats['rolling_OPS'] = daily_stats['OPS']
    else:
        # Rolling averages over the raw daily values
        daily_stats['rolling_BA'] = daily_stats['BA'].rolling(window=rolling_window, min_periods=1).mean()
        daily_stats['rolling_OBP'] = daily_stats['OBP'].rolling(window=rolling_window, min_periods=1).mean()
        daily_stats['rolling_SLG'] = daily_stats['SLG'].rolling(window=rolling_window, min_periods=1).mean()
        daily_stats['rolling_OPS'] = daily_stats['OPS'].rolling(window=rolling_window, min_periods=1).mean()



    return daily_stats


def plot_rolling_averages_for_pdf(hitter_id, rolling_avg_data, return_fig=False):
    """Generates a properly formatted rolling average chart for the PDF report."""

    # Fetch the player's name dynamically
    player_name = fetch_player_name(hitter_id)
    if not player_name:
        player_name = "Unknown Player"

    if rolling_avg_data is None or rolling_avg_data.empty:
        print(f"No rolling average data available for hitter ID: {hitter_id}")
        return None

    # Plot the rolling averages
    fig, ax = plt.subplots(figsize=(10, 6))
    stats_to_plot = ["rolling_BA", "rolling_OBP", "rolling_SLG", "rolling_OPS"]
    labels = ["BA (Batting Average)", "OBP (On-Base Percentage)", "SLG (Slugging Percentage)", "OPS"]
    colors = ["blue", "green", "orange", "red"]

    for stat, label, color in zip(stats_to_plot, labels, colors):
        if stat in rolling_avg_data.columns:
            ax.plot(
                rolling_avg_data["game_date"],
                rolling_avg_data[stat],
                label=label,
                color=color,
                linewidth=2,
                marker='o'  # <-- Add this
            )

    #Ensure consistent title formatting
    #ax.set_title(f"{player_name} - Rolling Averages (2025 Season)",
                 #fontsize=14, fontweight="bold", pad=15, loc='center')

    #Ensure labels are clearly visible
    #ax.set_xlabel("Game Date", fontsize=12, labelpad=8)
    #ax.set_ylabel("Statistic Value", fontsize=12, labelpad=8)

    #Ensure the legend is positioned properly (bottom center)
    ax.legend(title="Metrics", fontsize=12, loc='upper center',
              bbox_to_anchor=(0.5, -0.20), ncol=2, frameon=True)

    # Add a grid for better readability
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    # Format x-axis date labels
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%b %d"))
    plt.xticks(rotation=45)

    # Format y-axis values to three decimal places
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.3f}"))
    latest_date = rolling_avg_data["game_date"].max()
    season_start = pd.to_datetime("2025-03-27")
    ax.set_xlim(left=season_start, right=latest_date + pd.Timedelta(days=2))

    #Ensure tight layout so the title does not get cut off
    plt.tight_layout(rect=[0, 0, 1, 0.95])

    if return_fig:
        return plt.gcf()  # Return the figure for inclusion in the PDF
    else:
        plt.close(fig)



def generate_and_plot_rolling_averages(hitter_id, rolling_window=15, return_fig=False):

    # Step 1: Fetch and compute rolling averages
    rolling_avg_data = compute_rolling_averages_from_db(hitter_id, rolling_window)

    if rolling_avg_data is None or rolling_avg_data.empty:
        print(f"No rolling average data available for hitter ID: {hitter_id}")
        return None

    # Step 2: Plot rolling averages
    fig = plot_rolling_averages_for_pdf(hitter_id, rolling_avg_data, return_fig=return_fig)

    # Return the figure if needed (for PDF generation), otherwise just show it
    if return_fig:
        return fig
    else:
        plt.close(fig)

def generate_rolling_averages_visual(hitter_id, rolling_window=15):

    # Step 1: Fetch and compute rolling averages
    query = """
        SELECT
            game_date,
            CASE WHEN events IN ('single', 'double', 'triple', 'home_run') THEN 1 ELSE 0 END AS hit,
            CASE WHEN events IN ('walk', 'hit_by_pitch') THEN 1 ELSE 0 END AS on_base,
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
        WHERE batter_id = '%s'
            AND game_date >= '2025-01-01'
            AND game_date <= '2025-12-31'
        ORDER BY game_date;
    """

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query, (hitter_id,))
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()

        cursor.close()
        conn.close()

        pitch_data = pd.DataFrame(data, columns=columns)

        if pitch_data.empty:
            print(f" No rolling average data available for hitter ID: {hitter_id}")
            return None

    except Exception as e:
        print(f" Error fetching rolling averages data: {e}")
        return None

    # Step 2: Convert game_date to datetime
    pitch_data['game_date'] = pd.to_datetime(pitch_data['game_date'])

    # Step 3: Aggregate daily stats
    daily_stats = pitch_data.groupby('game_date').agg(
        hits=('hit', 'sum'),
        on_base=('on_base', 'sum'),
        total_bases=('total_bases', 'sum'),
        at_bats=('at_bat', 'sum')
    ).reset_index()

    # Step 4: Calculate cumulative stats
    daily_stats['cumulative_hits'] = daily_stats['hits'].cumsum()
    daily_stats['cumulative_on_base'] = daily_stats['on_base'].cumsum()
    daily_stats['cumulative_total_bases'] = daily_stats['total_bases'].cumsum()
    daily_stats['cumulative_at_bats'] = daily_stats['at_bats'].cumsum()

    # Step 5: Calculate metrics
    daily_stats['BA'] = daily_stats['cumulative_hits'] / daily_stats['cumulative_at_bats']
    daily_stats['OBP'] = (daily_stats['cumulative_hits'] + daily_stats['cumulative_on_base']) / (
        daily_stats['cumulative_at_bats'] + daily_stats['cumulative_on_base']
    )
    daily_stats['SLG'] = daily_stats['cumulative_total_bases'] / daily_stats['cumulative_at_bats']
    daily_stats['OPS'] = daily_stats['OBP'] + daily_stats['SLG']

    # Step 6: Compute rolling averages
    daily_stats['rolling_BA'] = daily_stats['BA'].rolling(rolling_window).mean()
    daily_stats['rolling_OBP'] = daily_stats['OBP'].rolling(rolling_window).mean()
    daily_stats['rolling_SLG'] = daily_stats['SLG'].rolling(rolling_window).mean()
    daily_stats['rolling_OPS'] = daily_stats['OPS'].rolling(rolling_window).mean()

    # Step 7: Fetch player's name
    player_name = fetch_player_name(hitter_id)
    if not player_name:
        player_name = "Unknown Player"

    # Step 8: Plot rolling averages
    fig, ax = plt.subplots(figsize=(10, 6))
    stats_to_plot = ["rolling_BA", "rolling_OBP", "rolling_SLG", "rolling_OPS"]
    labels = ["BA (Batting Average)", "OBP (On-Base Percentage)", "SLG (Slugging Percentage)", "OPS"]
    colors = ["blue", "green", "orange", "red"]

    for stat, label, color in zip(stats_to_plot, labels, colors):
        if stat in daily_stats.columns:
            ax.plot(daily_stats["game_date"], daily_stats[stat], label=label, color=color, linewidth=2)

    # Step 9: Customize plot
    ax.set_title(f"{player_name}'s Rolling Averages (2025 Season)", fontsize=20, weight="bold")
    ax.set_xlabel("Game Date", fontsize=12)
    ax.set_ylabel("Statistic Value", fontsize=12)
    ax.legend(title="Metrics", fontsize=12, loc='upper center', bbox_to_anchor=(0.5, -0.20), ncol=2)
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    # Step 10: Set x-axis date formatting
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%b %d"))
    plt.xticks(rotation=45)

    # Step 11: Format y-axis to show three decimal places
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.3f}"))

    plt.tight_layout()

    return fig  # This figure will be inserted into the hitter report
