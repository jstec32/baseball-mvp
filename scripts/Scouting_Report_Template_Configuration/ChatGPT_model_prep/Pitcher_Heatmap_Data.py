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


def generate_pitcher_hitter_heatmap_data(pitcher_id, hitter_id):
    """
    Generate combined heatmaps for each pitch type and return structured data for LLaMA.
    """
    apply_global_styles()
    print(f"Generating heatmaps and data for Pitcher ID: {pitcher_id} and Hitter ID: {hitter_id}...")

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

    structured_data = {
        "pitcher_name": pitcher_name,
        "hitter_name": hitter_name,
        "pitch_types": {}
    }

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

        # Collect structured data for the current pitch type
        structured_data["pitch_types"][pitch_type] = {
            "pitcher_whiff_rate": len(pitcher_pitch_data) / len(pitcher_data),
            "hitter_contact_rate": (
                len(hitter_pitch_data) / len(hitter_data)
                if not hitter_pitch_data.empty else 0
            ),
            "average_pitch_location": {
                "plate_x": pitcher_pitch_data['plate_x'].mean(),
                "plate_z": pitcher_pitch_data['plate_z'].mean()
            }
        }

        # Plot the heatmap
        ax = combined_axes[i] if num_pitch_types > 1 else combined_axes

        sns.kdeplot(
            x=pitcher_pitch_data['plate_x'],
            y=pitcher_pitch_data['plate_z'],
            cmap='Reds',
            fill=True,
            alpha=0.5,
            ax=ax,
            warn_singular=False,
            label=pitcher_name
        )

        if not hitter_pitch_data.empty:
            sns.kdeplot(
                x=hitter_pitch_data['plate_x'],
                y=hitter_pitch_data['plate_z'],
                cmap='Blues',
                fill=True,
                alpha=0.5,
                ax=ax,
                warn_singular=False,
                label=hitter_name
            )

        ax.add_patch(Rectangle((-0.83, 1.5), 1.66, 2.0, fill=False, color='black', linewidth=2))
        ax.set_xlim(-2.0, 2.0)
        ax.set_ylim(0.0, 5.0)
        ax.set_title(f'{pitch_type}', fontsize=14)
        ax.set_xlabel('Plate X', fontsize=12)
        if i == 0:
            ax.set_ylabel('Plate Z', fontsize=12)

    combined_fig.legend(
        handles=[
            plt.Line2D([0], [0], color='red', lw=4, label=pitcher_name),
            plt.Line2D([0], [0], color='blue', lw=4, label=hitter_name)
        ],
        loc='upper center',
        fontsize=12,
        bbox_to_anchor=(0.5, -0.05),
        ncol=2
    )
    combined_fig.tight_layout()

    print("Combined heatmap figure and structured data generated.")
    return {"structured_data": structured_data}



def test_generate_pitcher_hitter_heatmap_data():
    """
    Test the generate_pitcher_hitter_heatmap_data function with sample data.
    """
    # Example pitcher and hitter IDs
    pitcher_id = "605400"  # Replace with actual pitcher ID
    hitter_id = "518692"   # Replace with actual hitter ID

    # Call the function
    result = generate_pitcher_hitter_heatmap_data(pitcher_id, hitter_id)

    # Check if the result is not None
    if result is None:
        print("Function returned None. Test failed.")
        return

    # Validate structured data
    structured_data = result["structured_data"]
    print("Structured Data Output:")
    print(structured_data)

    # Ensure all keys are present
    required_keys = ["pitcher_name", "hitter_name", "pitch_types"]
    for key in required_keys:
        if key not in structured_data:
            print(f"Missing key in structured data: {key}. Test failed.")
            return

    # Validate pitch types in structured data
    if not structured_data["pitch_types"]:
        print("No pitch types found in structured data. Test failed.")
        return

    for pitch_type, metrics in structured_data["pitch_types"].items():
        print(f"Pitch Type: {pitch_type}")
        print(f"  - Pitcher Whiff Rate: {metrics['pitcher_whiff_rate']}")
        print(f"  - Hitter Contact Rate: {metrics['hitter_contact_rate']}")
        print(f"  - Average Pitch Location: {metrics['average_pitch_location']}")


    print("Test completed successfully.")

# Run the test
test_generate_pitcher_hitter_heatmap_data()
