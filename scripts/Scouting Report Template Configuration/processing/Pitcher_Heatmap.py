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


# SQL query to fetch pitch location data
def fetch_pitch_data(pitcher_id):
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
        # Execute the query and fetch the results
        cursor = connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return pd.DataFrame(results, columns=columns)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None
    finally:
        connection.close()


# Generate heatmaps with strike zone overlay
def generate_heatmaps(data):
    """
    Generate heatmaps for each pitch type with MLB strike zone overlay and standardized axes.
    """
    if data is None or data.empty:
        print("No data to generate heatmaps.")
        return

    for pitch in data['pitch_type'].unique():
        pitch_data = data[data['pitch_type'] == pitch]

        # Create the heatmap
        sns.kdeplot(x=pitch_data['plate_x'], y=pitch_data['plate_z'], cmap='Reds', fill=True)

        # Add MLB strike zone
        plt.gca().add_patch(Rectangle((-0.83, 1.5), 1.66, 2, fill=False, color='blue', linewidth=2))

        # Standardize axes for consistency
        plt.xlim(-2.0, 2.0)  # Standard horizontal limits
        plt.ylim(0.0, 5.0)   # Standard vertical limits

        # Set plot labels and title
        plt.title(f'Pitch Location Heatmap: {pitch}')
        plt.xlabel('Plate X')
        plt.ylabel('Plate Z')

        # Show plot
        plt.show()


# Main function
def main():
    pitcher_id = '453286'  # Example pitcher ID
    pitch_data = fetch_pitch_data(pitcher_id)

    if pitch_data is not None:
        print(f"Fetched {len(pitch_data)} rows of data.")
        generate_heatmaps(pitch_data)
    else:
        print("Failed to fetch pitch data.")


if __name__ == "__main__":
    main()

