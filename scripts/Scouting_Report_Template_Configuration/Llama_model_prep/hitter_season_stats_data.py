import pandas as pd
import matplotlib.pyplot as plt
import psycopg2
from scripts.Database_Configuration.visualization_config import  apply_global_styles

# Database configuration
DB_CONFIG = {
    "host": "aws-0-us-east-2.pooler.supabase.com",
    "database": "postgres",
    "user": "postgres.chcovbrcpmlxyauansqe",
    "password": "1Z4IO6fxxYw8PgxL",  # Replace with your Supabase password
    "port": 5432  # Default PostgreSQL port
}

# SQL query for the most recent season stats
SQL_QUERY = """
WITH players_with_team AS (
    SELECT 
        p.*, 
        t.abbreviation_games
    FROM players p
    JOIN teams t
        ON p."teamID" = t.abbreviation_players
),
most_recent_season AS (
    SELECT MAX(hs.season) AS season
    FROM hitter_season_statistics hs
    JOIN players_with_team pwt
        ON CONCAT(pwt."First_Name", ' ', pwt."Last_Name") = hs.name
    WHERE pwt.key_mlbam = %s
)
SELECT 
    hs.season,
    hs.batting_average AS ba,
    hs.on_base_percentage AS obp,
    hs.slugging_percentage AS slg,
    hs.home_runs AS hr,
    hs.rbi,
    hs.strikeouts,
    hs.walks,
    hs.ops,
    hs.ld_percent,
    hs.gb_percent,
    hs.fb_percent,
    hs.bb_percent,
    hs.k_percent
FROM hitter_season_statistics hs
JOIN players_with_team pwt
    ON CONCAT(pwt."First_Name", ' ', pwt."Last_Name") = hs.name
JOIN most_recent_season mrs
    ON hs.season = mrs.season
WHERE pwt.key_mlbam = %s;
"""

# SQL query to fetch the hitter's name
NAME_QUERY = """
SELECT CONCAT(p."First_Name", ' ', p."Last_Name") AS hitter_name
FROM players p
WHERE p.key_mlbam = %s;
"""

# Fetch most recent hitter stats
def fetch_recent_hitter_stats_and_name(key_mlbam):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Fetch the hitter's stats
        cursor.execute(SQL_QUERY, (key_mlbam, key_mlbam))
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()

        # Fetch the hitter's name
        cursor.execute(NAME_QUERY, (key_mlbam,))
        hitter_name = cursor.fetchone()[0]

        # Close connection
        cursor.close()
        conn.close()

        # Convert stats to a DataFrame
        stats_df = pd.DataFrame(data, columns=columns)

        return stats_df, hitter_name

    except Exception as e:
        print(f"Error fetching data: {e}")
        return None, None


# Main function for testing
def generate_hitter_season_stats_data(key_mlbam):
    """
    Fetch and process season stats for a given hitter ID and return structured data.
    """
    # Fetch hitter stats and name
    recent_hitter_stats, hitter_name = fetch_recent_hitter_stats_and_name(key_mlbam)

    if recent_hitter_stats is None or recent_hitter_stats.empty or hitter_name is None:
        print(f"Failed to fetch data for hitter ID: {key_mlbam}")
        return None

    print(f"Fetched stats for {hitter_name}.")

    # Summarize stats into structured data
    structured_data = {
        "hitter_id": key_mlbam,
        "name": hitter_name,
        "season_stats": []
    }

    for _, row in recent_hitter_stats.iterrows():
        structured_data["season_stats"].append({
            "season": row["season"],
            "ba": row.get("ba", None),  # Batting Average
            "obp": row.get("obp", None),  # On-Base Percentage
            "slg": row.get("slg", None),  # Slugging Percentage
            "ops": row.get("ops", None),  # On-Base Plus Slugging
            "hr": row.get("hr", None),  # Home Runs
            "rbi": row.get("rbi", None),  # Runs Batted In
            "strikeouts": row.get("strikeouts", None),  # Total Strikeouts
            "walks": row.get("walks", None)  # Total Walks
        })

    print("Structured data generated successfully.")
    return structured_data

if __name__ == "__main__":
    hitter_id = input("Enter Hitter ID: ").strip()
    result = generate_hitter_season_stats_data(hitter_id)

    if result:
        print("\nStructured Data Output:")
        print(result)
        print("\nSeason Stats:")
        for season in result["season_stats"]:
            print(f"Season: {season['season']}, BA: {season['ba']}, OBP: {season['obp']}, "
                  f"SLG: {season['slg']}, OPS: {season['ops']}, HR: {season['hr']}, "
                  f"RBI: {season['rbi']}, SO: {season['strikeouts']}, BB: {season['walks']}")
    else:
        print("No data found for the given hitter ID.")
