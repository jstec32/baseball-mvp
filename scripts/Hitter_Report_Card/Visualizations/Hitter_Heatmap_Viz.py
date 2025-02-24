import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2
from matplotlib.patches import Rectangle

from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Pitcher_Heatmap_Data import get_db_connection


# Fetch hitter data for heatmap visualization
def fetch_hitter_data_with_is_hit(hitter_id):
    """
    Fetch batted ball data for a specific hitter with positive outcomes.
    """
    query = f"""
    SELECT 
        pd.zone,
        pd.plate_x,
        pd.plate_z,
        pd.pitch_type,
        CASE 
            WHEN pd.events IN ('single', 'double', 'triple', 'home_run') THEN TRUE 
            ELSE FALSE 
        END AS is_hit
    FROM pitch_data pd
    WHERE pd.batter_id = '{hitter_id}' -- Specify the hitter ID
    ORDER BY pd.zone, pd.pitch_type;
    """
    connection = get_db_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return pd.DataFrame(results, columns=columns)
    except Exception as e:
        print(f"Error fetching hitter data: {e}")
        return None
    finally:
        connection.close()


def add_zones_to_strike_zone(ax):
    """
    Overlay numbered zones onto the strike zone.
    """
    zones = [
        (-0.71, 2.5, 0.47, 1.0, '1'), ( -0.24, 2.5, 0.47, 1.0, '2'), ( 0.23, 2.5, 0.47, 1.0, '3'),
        (-0.71, 1.5, 0.47, 1.0, '4'), ( -0.24, 1.5, 0.47, 1.0, '5'), ( 0.23, 1.5, 0.47, 1.0, '6'),
        (-0.71, 0.5, 0.47, 1.0, '7'), ( -0.24, 0.5, 0.47, 1.0, '8'), ( 0.23, 0.5, 0.47, 1.0, '9'),
    ]

    for x, y, width, height, label in zones:
        ax.add_patch(Rectangle((x, y), width, height, fill=False, edgecolor='black', linewidth=1))
        ax.text(x + width / 2, y + height / 2, label, ha='center', va='center', fontsize=8, color='black')


def generate_hitter_heatmap(hitter_id, hitter_name):

    # Fetch hitter data
    hitter_data = fetch_hitter_data_with_is_hit(hitter_id)

    if hitter_data is None or hitter_data.empty:
        print(f"No hitter data available for {hitter_name}.")
        return None

    hitter_data = hitter_data.dropna(subset=["plate_x", "plate_z"])

    if hitter_data.empty:
        print(f"No valid data for hitter {hitter_name}.")
        return None

    # Normalize hit weights for KDE plot
    weights = hitter_data['is_hit'].astype(int)
    if weights.sum() > 0:
        weights = weights / weights.sum()
    else:
        print(f"No hits found for {hitter_name}, skipping heatmap generation.")
        return None

    # Create figure
    fig, ax = plt.subplots(figsize=(6, 6))

    # Plot KDE heatmap for hitter success
    try:
        sns.kdeplot(
            x=hitter_data['plate_x'],
            y=hitter_data['plate_z'],
            cmap='Reds',
            fill=True,
            alpha=0.7,
            ax=ax,
            weights=hitter_data['is_hit'].astype(int)  # Weighted by hits
        )
    except Exception as e:
        print(f"Error generating hitter heatmap: {e}")
        return None

    # Add zones
    add_zones_to_strike_zone(ax)

    # Formatting
    ax.set_xlim(-2.0, 2.0)
    ax.set_ylim(0.0, 5.0)
    ax.set_title(f"Hitter Heatmap - {hitter_name}", fontsize=14)

    ax.set_xticks([])  # Hide x-axis ticks
    ax.set_yticks([])  # Hide y-axis ticks
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_frame_on(False)  # **Removes the frame**
    ax.axis('off')  # **Completely removes axis visuals**

    print(f" Hitter heatmap generated for {hitter_name}.")
    plt.show()
    return fig

generate_hitter_heatmap("621566", "Matt Olson")

