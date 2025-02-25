import pandas as pd
import psycopg2

from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Pitcher_Heatmap_Data import get_db_connection


def fetch_critical_moments(game_id):
    """
    Fetch the highest leverage moments based on absolute delta_run_exp.
    """
    query = f"""
    SELECT 
    players."First_Name" || ' ' || players."Last_Name" AS batter_name,
    inning, 
    inning_topbot, 
    pitch_type, 
    delta_run_exp::NUMERIC AS leverage_value, 
    ABS(delta_run_exp::NUMERIC) AS leverage_impact, 
    events, 
    launch_speed
FROM pitch_data
JOIN players ON pitch_data.batter_id = players.key_mlbam
WHERE game_id = '{game_id}'  -- Cast to numeric before comparison
ORDER BY leverage_impact DESC  -- Sort by absolute impact
LIMIT 5;
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
        print(f"Error fetching critical moments: {e}")
        return None
    finally:
        connection.close()


# Example usage
game_id = '746196'  # Replace with actual game_id
critical_moments_table = fetch_critical_moments(game_id)

if not critical_moments_table.empty:
    print("Critical Moments Table:")
    print(critical_moments_table.to_string(index=False))  # Prints DataFrame neatly
else:
    print("No critical moments found.")
