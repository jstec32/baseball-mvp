import psycopg2
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


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


# Main function
def main():
    pitcher_id = '453286'  # Example pitcher ID
    hitter_id = '664023'  # Example hitter ID

    pitcher_data = fetch_pitcher_data(pitcher_id)
    hitter_data = fetch_hitter_data(hitter_id)

    if pitcher_data is not None and hitter_data is not None:
        print(f"Fetched {len(pitcher_data)} rows of pitcher data.")
        print(f"Fetched {len(hitter_data)} rows of hitter data.")
        generate_combined_heatmaps(pitcher_data, hitter_data)
    else:
        print("Failed to fetch data.")


if __name__ == "__main__":
    main()

