import os

import psycopg2
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from matplotlib.patches import Rectangle
from scripts.Database_Configuration.visualization_config import  apply_global_styles

#Fetch player name
def fetch_player_name(player_id):

    query = """
    SELECT CONCAT("First_Name", ' ', "Last_Name") AS player_name
    FROM players
    WHERE key_mlbam = %s;
    """
    connection = get_db_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute(query, (player_id,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error fetching player name: {e}")
        return None



# Database connection function
def get_db_connection():
    """
    Establish and return a connection to the Supabase PostgreSQL database.
    """
    load_dotenv()
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            port=os.getenv("DB_PORT")
        )
        print("Connected to Supabase PostgreSQL database successfully!")
        return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to database: {e}")
        return None


# SQL queries for pitcher and hitter data
def fetch_pitcher_data(pitcher_id):
    """
    Fetch pitch type and location data for a specific pitcher.
    """
    query = f"""
    SELECT 
        pd.pitch_type,
        pd.plate_x,
        pd.plate_z
    FROM pitch_data pd
    WHERE pd.pitcher_id = '{pitcher_id}'
      AND pd.description IN ('called_strike', 'swinging_strike', 'foul', 'hit_into_play')
      AND pd.pitch_type IS NOT NULL
    ORDER BY pd.pitch_type;
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
        print(f"Error fetching pitcher data: {e}")
        return None
    finally:
        connection.close()


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

    # Zone coordinates (x, y, width, height)
    zones = [
        (-0.71, 2.5, 0.47, 1.0, '1'), ( -0.24, 2.5, 0.47, 1.0, '2'), ( 0.23, 2.5, 0.47, 1.0, '3'),
        (-0.71, 1.5, 0.47, 1.0, '4'), ( -0.24, 1.5, 0.47, 1.0, '5'), ( 0.23, 1.5, 0.47, 1.0, '6'),
        (-0.71, 0.5, 0.47, 1.0, '7'), ( -0.24, 0.5, 0.47, 1.0, '8'), ( 0.23, 0.5, 0.47, 1.0, '9'),
    ]

    for x, y, width, height, label in zones:
        # Draw zone rectangle
        ax.add_patch(Rectangle((x, y), width, height, fill=False, edgecolor='black', linewidth=1))
        # Add zone number
        ax.text(x + width / 2, y + height / 2, label, ha='center', va='center', fontsize=8, color='black')


# Generate combined heatmap for each pitch type
def generate_combined_heatmaps(pitcher_data, hitter_data, pitcher_name, hitter_name):

    if pitcher_data is None or pitcher_data.empty:
        print("No pitcher data available.")
        return
    if hitter_data is None or hitter_data.empty:
        print("No hitter data available.")
        return

    pitch_types = pitcher_data['pitch_type'].unique()
    num_pitch_types = len(pitch_types)

    # Create figure for combined heatmaps
    combined_fig, combined_axes = plt.subplots(
        1, num_pitch_types, figsize=(6 * num_pitch_types, 6), sharey=True
    )
    combined_fig.subplots_adjust(left=0.1, right=0.9)
    #combined_fig.subplots_adjust(bottom=0.15)

    for i, pitch_type in enumerate(pitch_types):
        pitcher_pitch_data = pitcher_data[pitcher_data['pitch_type'] == pitch_type]
        hitter_pitch_data = hitter_data[hitter_data['pitch_type'] == pitch_type]

        pitcher_pitch_data = pitcher_pitch_data.dropna(subset=["plate_x", "plate_z"])
        hitter_pitch_data = hitter_pitch_data.dropna(subset=["plate_x", "plate_z"])

        print(f"Pitch type: {pitch_type}")
        print(f"Pitcher data:\n{pitcher_pitch_data.describe()}")
        print(f"Hitter data:\n{hitter_pitch_data.describe()}")

        if pitcher_pitch_data.empty:
            print(f"Skipping {pitch_type}: No valid data for pitcher.")
            continue
        if hitter_pitch_data.empty:
            print(f"Skipping {pitch_type}: No valid data for hitter.")
            continue
        if len(pitcher_pitch_data) < 2:
            print(f"Skipping {pitch_type}: Insufficient data for pitcher heatmap ({len(pitcher_pitch_data)} points).")
            continue
        if len(hitter_pitch_data) < 2:
            print(f"Skipping {pitch_type}: Insufficient data for hitter heatmap ({len(hitter_pitch_data)} points).")
            continue

        ax = combined_axes[i] if num_pitch_types > 1 else combined_axes

        weights = hitter_pitch_data['is_hit'].astype(int)
        if weights.sum() > 0:
            weights = weights / weights.sum()
        else:
            print(f"Skipping {pitch_type}: No hits for hitter data.")
            continue

        # Plot pitcher heatmap

        try:
            sns.kdeplot(
                x=pitcher_pitch_data['plate_x'],
                y=pitcher_pitch_data['plate_z'],
                cmap='Reds',
                fill=True,
                alpha=0.3,
                ax=ax,
                warn_singular=False,
                label=f"{pitcher_name} Density"
            )
        except Exception as e:
            print(f"Error generating pitcher KDE for {pitch_type}: {e}")
        # Plot hitter heatmap
        try:
            sns.kdeplot(
                x=hitter_pitch_data['plate_x'],
                y=hitter_pitch_data['plate_z'],
                cmap='Blues',
                fill=True,
                alpha=0.5,
                ax=ax,
                weights=hitter_pitch_data['is_hit'].astype(int),  # Weighted by hits
                label=f"{hitter_name} Hit Density"
            )
        except Exception as e:
            print(f"Error generating hitter KDE for {pitch_type}: {e}")

        # Add zones to the strike zone
        add_zones_to_strike_zone(ax)

        # Set axis limits and labels
        ax.set_xlim(-2.0, 2.0)  # Horizontal scaling
        ax.set_ylim(0.0, 5.0)  # Vertical scaling

        ax.set_title(f'{pitch_type}', fontsize=14)
        ax.set_xlabel("Plate X", fontsize=10)
        if i == 0:
            ax.set_ylabel("Plate Z", fontsize=10)


    # Add a combined legend at the bottom of the figure
    handles = [
        plt.Line2D([0], [0], color='red', lw=4, label=pitcher_name),
        plt.Line2D([0], [0], color='blue', lw=4, label=hitter_name),
    ]

    # Adjust layout to make room for the legend at the bottom
    #combined_fig.subplots_adjust(bottom=0.05)

    combined_fig.legend(
        handles=handles,
        loc='lower center',
        fontsize=12,
        bbox_to_anchor=(0.5, 0),  # Adjust position to leave space
        ncol=2  # Horizontal layout
    )

    combined_fig.subplots_adjust(left=0.025, right=0.975,top = 0.85, bottom = 0.2)
    print("Combined heatmap figure generated in memory.")
    return combined_fig

def generate_pitcher_heatmap_visual(pitcher_id, hitter_id):

    print(f"Generating heatmaps for Pitcher ID: {pitcher_id} and Hitter ID: {hitter_id}...")

    # Fetch pitcher and hitter names
    pitcher_name = fetch_player_name(pitcher_id)
    hitter_name = fetch_player_name(hitter_id)

    if not pitcher_name or not hitter_name:
        print("Error: Failed to fetch pitcher or hitter names.")
        return None

    print(f"Pitcher: {pitcher_name}, Hitter: {hitter_name}")

    # Fetch pitcher and hitter data
    pitcher_data = fetch_pitcher_data(pitcher_id)
    hitter_data = fetch_hitter_data_with_is_hit(hitter_id)

    # Validate data
    if pitcher_data is None or pitcher_data.empty:
        print("No pitcher data available.")
        return None
    if hitter_data is None or hitter_data.empty:
        print("No hitter data available.")
        return None

    # Generate combined heatmaps and return the figure
    return generate_combined_heatmaps(pitcher_data, hitter_data, pitcher_name, hitter_name)

if __name__ == "__main__":
    pitcher_id = input("Enter Pitcher ID: ")
    hitter_id = input("Enter Hitter ID: ")

    # Generate combined heatmaps
    result = generate_pitcher_heatmap_visual(pitcher_id, hitter_id)

    if result:
        print("Combined heatmap generated in memory.")
        plt.show()  # Display the heatmap
    else:
        print("Failed to generate heatmaps.")