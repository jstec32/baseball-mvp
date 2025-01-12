import psycopg2
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
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
    try:
        conn = psycopg2.connect(
            host="aws-0-us-east-2.pooler.supabase.com",
            database="postgres",
            user="postgres.chcovbrcpmlxyauansqe",
            password="1Z4IO6fxxYw8PgxL",  # Replace with your Supabase password
            port=5432
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


def fetch_hitter_data(hitter_id):
    """
    Fetch batted ball data for a specific hitter with positive outcomes.
    """
    query = f"""
    SELECT 
        pd.pitch_type,
        pd.plate_x,
        pd.plate_z,
        pd.launch_speed
    FROM pitch_data pd
    WHERE pd.batter_id = '{hitter_id}'
      AND pd.events IN ('single', 'double', 'triple', 'home_run')
      AND pd.launch_speed IS NOT NULL
    ORDER BY pd.launch_speed DESC;
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


# Generate combined heatmap for each pitch type
def generate_combined_heatmaps(pitcher_data, hitter_data):
    """
    Generate combined heatmaps for each pitch type.
    """
    apply_global_styles()

    if pitcher_data is None or pitcher_data.empty:
        print("No pitcher data available.")
        return
    if hitter_data is None or hitter_data.empty:
        print("No hitter data available.")
        return

    pitch_types = pitcher_data['pitch_type'].unique()
    for pitch_type in pitch_types:
        pitcher_pitch_data = pitcher_data[pitcher_data['pitch_type'] == pitch_type]
        hitter_pitch_data = hitter_data[hitter_data['pitch_type'] == pitch_type]

        # Plot pitcher heatmap
        sns.kdeplot(x=pitcher_pitch_data['plate_x'], y=pitcher_pitch_data['plate_z'], cmap='Reds', fill=True, alpha=0.5)

        # Plot hitter heatmap
        if not hitter_pitch_data.empty:
            sns.kdeplot(x=hitter_pitch_data['plate_x'], y=hitter_pitch_data['plate_z'], cmap='Blues', fill=True,
                        alpha=0.5)

        # Add MLB strike zone
        plt.gca().add_patch(Rectangle((-0.83, 1.5), 1.66, 2, fill=False, color='black', linewidth=2))

        # Standardize axes for consistency
        plt.xlim(-2.0, 2.0)
        plt.ylim(0.0, 5.0)

        # Set plot labels and title
        plt.title(f'Combined Heatmap for {pitch_type}')
        plt.xlabel('Plate X')
        plt.ylabel('Plate Z')

        # Add custom legend
        plt.legend(handles=[
            plt.Line2D([0], [0], color='red', lw=4, label='Pitcher'),
            plt.Line2D([0], [0], color='blue', lw=4, label='Hitter')
        ])

        # Show plot
        plt.show()


def generate_pitcher_heatmap_visual(pitcher_id, hitter_id):
    apply_global_styles()
    print(f"Generating heatmaps for Pitcher ID: {pitcher_id} and Hitter ID: {hitter_id}...")

    # Fetch pitcher and hitter names
    pitcher_name = fetch_player_name(pitcher_id)
    hitter_name = fetch_player_name(hitter_id)

    if not pitcher_name or not hitter_name:
        print("Error: Failed to fetch pitcher or hitter names.")
        return None

    # Fetch pitcher and hitter data
    pitcher_data = fetch_pitcher_data(pitcher_id)
    hitter_data = fetch_hitter_data(hitter_id)

    if pitcher_data is None or pitcher_data.empty:
        print("No pitcher data available.")
        return None
    if hitter_data is None or hitter_data.empty:
        print("No hitter data available.")
        return None

    pitch_types = pitcher_data['pitch_type'].unique()
    num_pitch_types = len(pitch_types)

    # Create a figure for the combined heatmaps
    combined_fig, combined_axes = plt.subplots(
        1, num_pitch_types, figsize=(6 * num_pitch_types, 6), sharey=True
    )

    for i, pitch_type in enumerate(pitch_types):
        # Filter data by pitch type
        pitcher_pitch_data = pitcher_data[pitcher_data['pitch_type'] == pitch_type]
        hitter_pitch_data = hitter_data[hitter_data['pitch_type'] == pitch_type]

        ax = combined_axes[i] if num_pitch_types > 1 else combined_axes  # Handle single subplot case

        # Plot pitcher heatmap
        sns.kdeplot(
            x=pitcher_pitch_data['plate_x'],
            y=pitcher_pitch_data['plate_z'],
            cmap='Reds',
            fill=True,
            alpha=0.5,
            ax=ax,
            warn_singular=False,
            label=pitcher_name  # Use dynamic pitcher name
        )

        # Plot hitter heatmap (if data exists for the pitch type)
        if not hitter_pitch_data.empty:
            sns.kdeplot(
                x=hitter_pitch_data['plate_x'],
                y=hitter_pitch_data['plate_z'],
                cmap='Blues',
                fill=True,
                alpha=0.5,
                ax=ax,
                warn_singular=False,
                label=hitter_name  # Use dynamic hitter name
            )

        # Add MLB strike zone
        ax.add_patch(Rectangle(
            (-0.83, 1.5),  # Bottom-left corner of the strike zone
            1.66,  # Width of the strike zone
            2.0,  # Height of the strike zone
            fill=False,
            color='black',
            linewidth=2
        ))

        # Standardize axes for consistency across all heatmaps
        ax.set_xlim(-2.0, 2.0)
        ax.set_ylim(0.0, 5.0)

        # Set plot title
        ax.set_title(f'{pitch_type}', fontsize=14)
        ax.set_xlabel('Plate X', fontsize=12)
        if i == 0:
            ax.set_ylabel('Plate Z', fontsize=12)  # Only set ylabel for the first plot

        # Add a combined title for the entire figure
        combined_fig.suptitle(
            f"Heatmap Analysis: {hitter_name} vs. {pitcher_name}",
            fontsize=16,
            y=0.98  # Adjust y-position of the title
        )

    # Add a combined legend for the entire figure
    handles = [
        plt.Line2D([0], [0], color='red', lw=4, label=pitcher_name),
        plt.Line2D([0], [0], color='blue', lw=4, label=hitter_name)
    ]
    combined_fig.legend(
        handles=handles,
        loc='upper center',
        fontsize=12,
        bbox_to_anchor=(0.5, -0.05),  # Adjust to position below the plots
        ncol=2  # Horizontal layout for the legend
    )

    combined_fig.tight_layout()
    print("Combined heatmap figure generated in memory.")
    return combined_fig  # Return the Matplotlib figure directly

if __name__ == "__main__":
    pitcher_id = input("Enter Pitcher ID: ")
    hitter_id = input("Enter Hitter ID: ")

    result = generate_pitcher_heatmap_visual(pitcher_id, hitter_id)

    if result:
        print(f"Combined heatmap saved at: {result['combined_heatmap_path']}")
        # Display the combined heatmap
        plt.imshow(plt.imread(result['combined_heatmap_path']))
        plt.axis('off')
        plt.show()
    else:
        print("Failed to generate heatmaps.")
