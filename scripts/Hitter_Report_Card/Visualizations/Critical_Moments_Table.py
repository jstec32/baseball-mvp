import pandas as pd
import psycopg2


def fetch_critical_moments(game_id):
    """
    Fetch the highest leverage moments based on absolute delta_run_exp.
    """
    query = f"""
    SELECT 
        players.first_name || ' ' || players.last_name AS batter_name,
        inning, 
        inning_topbot, 
        pitch_type, 
        ABS(delta_run_exp) AS leverage_value, 
        events, 
        launch_speed
    FROM statcast_data
    JOIN players ON statcast_data.batter_id = players.key_mlbam
    WHERE game_id = '{game_id}'
    ORDER BY leverage_value DESC
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
game_id = "20241001"  # Replace with actual game_id
critical_moments_table = fetch_critical_moments(game_id)

if critical_moments_table is not None:
    import ace_tools as tools

    tools.display_dataframe_to_user(name="Critical Moments Table", dataframe=critical_moments_table)
else:
    print("No critical moments found.")
