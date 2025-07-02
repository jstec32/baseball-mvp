import pandas as pd
import psycopg2
import seaborn as sns
import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from sqlalchemy import create_engine
from scripts.Scouting_Report_Template_Configuration.db_config.db_connection import clear_memory

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

def generate_pitcher_performance_chart(data):

    # Step 1: Define metrics
    hit_events = ['single', 'double', 'triple', 'home_run']
    out_events = ['strikeout', 'field_out', 'grounded_into_double_play', 'force_out', 'sac_fly']
    non_at_bat_events = ['walk', 'hit_by_pitch', 'sac_bunt', 'catcher_interf']

    # Step 2: Add pitch-level flags
    data['is_hit'] = data['events'].isin(hit_events).astype(int)
    data['is_walk'] = (data['events'] == 'walk').astype(int)
    data['is_hbp'] = (data['events'] == 'hit_by_pitch').astype(int)
    data['is_strikeout'] = (data['events'] == 'strikeout').astype(int)
    data['is_home_run'] = (data['events'] == 'home_run').astype(int)
    data['is_out'] = data['events'].isin(out_events).astype(int)

    # Step 3: Group by count to calculate aggregated metrics
    grouped = data.groupby('count').agg(
        Plate_Appearances=('events', lambda x: (~x.isna()).sum()),  # Total plate appearances
        Hits_Allowed=('is_hit', 'sum'),  # Hits allowed
        Walks=('is_walk', 'sum'),  # Walks allowed
        HBP = ('is_hbp', 'sum'), #HBP allowed
        Strikeouts=('is_strikeout', 'sum'),  # Strikeouts
        Home_Runs=('is_home_run', 'sum'),  # Home runs allowed
        Outs=('is_out', 'sum'),
        Earned_Runs=('events', lambda x: x.isin(hit_events).sum()),  # Earned runs
        At_Bats=('events', lambda x: (~x.isin(non_at_bat_events) & x.notna()).sum()),  # At-bats
        Total_Bases_Allowed=('events', lambda x: (
            (x == 'single').sum() +
            2 * (x == 'double').sum() +
            3 * (x == 'triple').sum() +
            4 * (x == 'home_run').sum()
        )),  # Total bases allowed
    ).reset_index()

    grouped['Innings_Pitched'] = (grouped['Outs'] / 3).round(2)
    # Step 4: Calculate pitcher-specific metrics

    grouped['HR%'] = ((grouped['Home_Runs'] / grouped['Plate_Appearances']) * 100).round(2)
    grouped['Opp_BA'] = (grouped['Hits_Allowed'] / grouped['At_Bats']).round(3)
    grouped['Opp_SLUG'] = (grouped['Total_Bases_Allowed'] / grouped['At_Bats']).round(3)
    grouped['ERA'] = ((grouped['Earned_Runs'] * 9) / grouped['Plate_Appearances']).round(2)


    # Step 5: Calculate most common pitch type for each count
    pitch_counts = data.groupby(['count', 'pitch_type']).size().reset_index(name='Pitch_Count')
    total_pitches = pitch_counts.groupby('count')['Pitch_Count'].sum().reset_index(name='Total_Pitches')
    pitch_counts = pitch_counts.merge(total_pitches, on='count')
    pitch_counts['Pitch_Percentage'] = (pitch_counts['Pitch_Count'] / pitch_counts['Total_Pitches'] * 100).round(2)
    most_common_pitch = pitch_counts.loc[pitch_counts.groupby('count')['Pitch_Percentage'].idxmax()]
    most_common_pitch = most_common_pitch[['count', 'pitch_type', 'Pitch_Percentage']].rename(
        columns={'pitch_type': 'Most_Common_Pitch', 'Pitch_Percentage': 'Most_Common_Pitch_Percentage'}
    )

    # Step 6: Merge most common pitch information into aggregated stats
    final_data = grouped.merge(most_common_pitch, on='count', how='left')


    return final_data

def convert_to_structured_data_pitcher(dataframe):

    structured_data = {}
    for _, row in dataframe.iterrows():
        structured_data[row['count']] = {
            'Plate_Appearances': row['Plate_Appearances'],
            'Hits_Allowed': row['Hits_Allowed'],
            'Walks': row['Walks'],
            'HBP': row['HBP'],
            'Strikeouts': row['Strikeouts'],
            'Home_Runs': row['Home_Runs'],
            'Innings_Pitched': row['Innings_Pitched'],
            'HR%': row['HR%'],
            'Opp_BA': row['Opp_BA'],
            'Opp_SLUG': row['Opp_SLUG'],
            'ERA': row['ERA'],
            'Most_Common_Pitch': row['Most_Common_Pitch'],
            'Most_Common_Pitch_Percentage': row['Most_Common_Pitch_Percentage']
        }
    print("Structured data generated successfully.")
    return structured_data


