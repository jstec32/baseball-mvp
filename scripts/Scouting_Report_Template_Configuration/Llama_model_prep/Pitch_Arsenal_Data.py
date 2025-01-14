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

# SQL query template
SQL_QUERY_TEMPLATE = """
SELECT 
    pitch_type, 
    ROUND(CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS NUMERIC), 2) AS usage_percent,
    ROUND(CAST(AVG(release_speed) AS NUMERIC), 2) AS avg_velocity,
    ROUND(CAST(AVG(pfx_x) AS NUMERIC), 2) AS avg_horizontal_break,
    ROUND(CAST(AVG(pfx_z) AS NUMERIC), 2) AS avg_vertical_break,
    ROUND(CAST(SUM(CASE WHEN description = 'swinging_strike' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS NUMERIC), 2) AS whiff_percent,
    ROUND(CAST(SUM(CASE WHEN description = 'called_strike' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS NUMERIC), 2) AS strike_percent
FROM pitch_data
WHERE pitcher_id = %s
GROUP BY pitch_type
ORDER BY usage_percent DESC;
"""

# Fetch data from the database
def fetch_pitch_arsenal(pitcher_id):
    try:
        # Connect to the database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Execute the query with the dynamic pitcher_id
        cursor.execute(SQL_QUERY_TEMPLATE, (pitcher_id,))
        columns = [desc[0] for desc in cursor.description]
        data = cursor.fetchall()

        # Close connection
        cursor.close()
        conn.close()

        # Convert data to a DataFrame
        return pd.DataFrame(data, columns=columns)

    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

# Generate a bar chart for Usage Rate
def plot_usage_rate(data, pitcher_id, return_fig=False):
    apply_global_styles()

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(data['pitch_type'], data['usage_percent'], color='skyblue')

    # Add labels
    for i, value in enumerate(data['usage_percent']):
        ax.text(i, value + 1, f"{value:.2f}%", ha='center', fontsize=10)

    # Chart customization

    ax.set_ylabel("Usage %", fontsize=12)
    ax.set_xlabel("Pitch Type", fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()

    if return_fig:
        return fig
    else:
        plt.show()


# Generate a table for other stats
def plot_pitch_arsenal_table(data, pitcher_id, return_fig=False):
    apply_global_styles()

    fig, ax = plt.subplots(figsize=(4, len(data) * 0.6))  # Adjust height based on rows
    ax.axis('tight')
    ax.axis('off')

    # Create the table
    table = ax.table(
        cellText=data.values,
        colLabels=data.columns,
        cellLoc='center',
        loc='center'
    )

    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(col=list(range(len(data.columns))))


    if return_fig:
        return fig
    else:
        plt.show()


def generate_pitch_arsenal_data(pitcher_id):

    # Fetch the data
    pitch_arsenal_data = fetch_pitch_arsenal(pitcher_id)

    if pitch_arsenal_data is None or pitch_arsenal_data.empty:
        print(f"No pitch arsenal data available for pitcher_id: {pitcher_id}")
        return None

    print(f"Fetched {len(pitch_arsenal_data)} rows of pitch arsenal data for pitcher_id: {pitcher_id}")

    # Summarize the data into structured JSON-like format
    structured_data = {
        "pitcher_id": pitcher_id,
        "arsenal": []
    }

    for _, row in pitch_arsenal_data.iterrows():
        structured_data["arsenal"].append({
            "pitch_type": row["pitch_type"],
            "usage_percent": row["usage_percent"],
            "avg_velocity": row["avg_velocity"],
            "avg_horizontal_break": row["avg_horizontal_break"],
            "avg_vertical_break": row["avg_vertical_break"],
            "whiff_percent": row["whiff_percent"],
            "strike_percent": row["strike_percent"]
        })

    print("Structured data generated successfully.")
    return structured_data

if __name__ == "__main__":
    pitcher_id = input("Enter Pitcher ID: ").strip()
    result = generate_pitch_arsenal_data(pitcher_id)

    if result:
        print("\nStructured Data Output:")
        print(result)
        print("\nPitch Arsenal Summary:")
        for pitch in result["arsenal"]:
            print(f"Pitch Type: {pitch['pitch_type']}, Usage: {pitch['usage_percent']}%, "
                  f"Velocity: {pitch['avg_velocity']} mph, H-Break: {pitch['avg_horizontal_break']}, "
                  f"V-Break: {pitch['avg_vertical_break']}, Whiff%: {pitch['whiff_percent']}%, "
                  f"Strike%: {pitch['strike_percent']}%")
    else:
        print("No data found for the given pitcher ID.")
