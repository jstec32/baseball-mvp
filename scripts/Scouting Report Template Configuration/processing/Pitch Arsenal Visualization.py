import pandas as pd
import matplotlib.pyplot as plt
import psycopg2

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
def plot_usage_rate(data, pitcher_id):
    if data is None or data.empty:
        print("No data to visualize.")
        return

    # Bar chart for Usage %
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(data['pitch_type'], data['usage_percent'], color='skyblue')

    # Add labels
    for i, value in enumerate(data['usage_percent']):
        ax.text(i, value + 1, f"{value:.2f}%", ha='center', fontsize=10)

    # Chart customization
    ax.set_title(f"Pitch Usage Rate for Pitcher (ID: {pitcher_id})", fontsize=16)
    ax.set_ylabel("Usage %", fontsize=12)
    ax.set_xlabel("Pitch Type", fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.show()

# Generate a table for other stats
def plot_pitch_arsenal_table(data, pitcher_id):
    if data is None or data.empty:
        print("No data to visualize.")
        return

    # Visualization: Table
    fig, ax = plt.subplots(figsize=(10, len(data) * 0.5))  # Adjust height based on rows
    ax.axis('tight')
    ax.axis('off')

    # Remove usage_percent column since it's visualized in the bar chart
    data_for_table = data

    # Create the table
    table = ax.table(
        cellText=data_for_table.values,
        colLabels=data_for_table.columns,
        cellLoc='center',
        loc='center'
    )

    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(col=list(range(len(data_for_table.columns))))

    # Add a title
    plt.title(f"Pitch Arsenal Details for Pitcher (ID: {pitcher_id})", fontsize=14)
    plt.show()

# Main function for manual testing
def main():
    # Replace with the desired pitcher_id for testing
    pitcher_id = "543037"  # Example pitcher_id

    # Fetch the data
    pitch_arsenal_data = fetch_pitch_arsenal(pitcher_id)

    # Visualize usage rate
    plot_usage_rate(pitch_arsenal_data, pitcher_id)

    # Visualize pitch arsenal table
    plot_pitch_arsenal_table(pitch_arsenal_data, pitcher_id)

if __name__ == "__main__":
    main()



