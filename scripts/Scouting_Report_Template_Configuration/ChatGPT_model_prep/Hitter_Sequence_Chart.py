import pandas as pd
import psycopg2
import seaborn as sns
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from sqlalchemy import create_engine
from scripts.Scouting_Report_Template_Configuration.db_config.db_connection import clear_memory

# Database connection details
import os
load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432))  # Default port 5432 if not set
}



def fetch_statcast_data(batter_id=None, pitcher_id=None):

    # Create the SQL query
    query = """
    SELECT *
    FROM pitch_data
    WHERE TRUE
    """
    if batter_id is not None:
        query += f" AND batter_id = '{batter_id}'"  # Convert batter_id to string in the query
    if pitcher_id is not None:
        query += f" AND pitcher_id = '{pitcher_id}'"  # Convert pitcher_id to string if needed

    # Connect to the database and execute the query
    try:
        conn = psycopg2.connect(**db_config)
        data = pd.read_sql_query(query, conn)
        conn.close()
        print("Successfully fetched data from the database.")
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

import pandas as pd
import os

def generate_hitter_performance_chart(data):
    """
    Generate hitter performance metrics grouped by count.
    """
    # Step 1: Define what counts as hits and at-bats
    hit_events = ['single', 'double', 'triple', 'home_run']
    non_at_bat_events = ['walk', 'hit_by_pitch', 'sac_bunt', 'sac_fly', 'catcher_interf']

    data['is_swing'] = data['description'].str.contains(r'(swing|foul|hit_into_play)', case=False, na=False).astype(int)
    data['is_whiff'] = data['description'].str.contains(r'swinging_strike', case=False, na=False).astype(int)

    # Step 2: Group by count and calculate metrics
    grouped = data.groupby('count').agg(
        Hits=('events', lambda x: x.isin(hit_events).sum()),  # Count hits
        At_Bats=('events', lambda x: (~x.isin(non_at_bat_events) & x.notna()).sum()),  # Count at-bats
        Walks=('events', lambda x: (x == 'walk').sum()),  # Count walks
        Hit_By_Pitch=('events', lambda x: (x == 'hit_by_pitch').sum()),  # Count HBPs
        Sac_Flies=('events', lambda x: (x == 'sac_fly').sum()),  # Count sac flies
        Total_Bases=('events', lambda x: (
            (x == 'single').sum() +
            2 * (x == 'double').sum() +
            3 * (x == 'triple').sum() +
            4 * (x == 'home_run').sum()
        )),  # Calculate total bases
        Swings=('is_swing', 'sum'),  # Total swings (aggregated from pitch level)
        Whiffs=('is_whiff', 'sum')  # Total whiffs (aggregated from pitch level)
    ).reset_index()

    # Step 3: Calculate batting metrics
    grouped['BA'] = (grouped['Hits'] / grouped['At_Bats']).round(3)
    grouped['OBP'] = ((grouped['Hits'] + grouped['Walks'] + grouped['Hit_By_Pitch']) /
                      (grouped['At_Bats'] + grouped['Walks'] + grouped['Hit_By_Pitch'] + grouped['Sac_Flies'])).round(3)
    grouped['SLG'] = (grouped['Total_Bases'] / grouped['At_Bats']).round(3)
    grouped['OPS'] = (grouped['OBP'] + grouped['SLG']).round(3)
    grouped['Whiff_Rate'] = (grouped['Whiffs'] / grouped['Swings'].clip(lower=1)).round(3)

    return grouped

def convert_to_structured_data_hitter(dataframe):
    """
    Convert the hitter performance DataFrame into structured data.
    """
    structured_data = {}
    for _, row in dataframe.iterrows():
        structured_data[row['count']] = {
            'Hits': row['Hits'],
            'At_Bats': row['At_Bats'],
            'Walks': row['Walks'],
            'Hit_By_Pitch': row['Hit_By_Pitch'],
            'Sac_Flies': row['Sac_Flies'],
            'Total_Bases': row['Total_Bases'],
            'Swings': row['Swings'],
            'Whiffs': row['Whiffs'],
            'BA': row['BA'],
            'OBP': row['OBP'],
            'SLG': row['SLG'],
            'OPS': row['OPS'],
            'Whiff_Rate': row['Whiff_Rate']
        }
    print("Structured data generated successfully.")
    return structured_data

