import pandas as pd
import psycopg2

# Database configuration
DB_CONFIG = {
    "host": "aws-0-us-east-2.pooler.supabase.com",
    "database": "postgres",
    "user": "postgres.chcovbrcpmlxyauansqe",
    "password": "1Z4IO6fxxYw8PgxL",  # Replace with your Supabase password
    "port": 5432  # Default PostgreSQL port
}

# Path to your existing CSV file
CSV_PATH = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/season_pitching_statistics.csv"

# Path to save the updated CSV file
OUTPUT_CSV_PATH = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/rowidseason_pitching_statistics.csv"

# Load the CSV into a DataFrame
data = pd.read_csv(CSV_PATH)

# Add a 'row_id' column starting from 1
data.insert(0, 'row_id', range(1, len(data) + 1))

# Save the updated DataFrame back to a new CSV file
data.to_csv(OUTPUT_CSV_PATH, index=False)

print(f"Updated CSV saved to {OUTPUT_CSV_PATH} with 'row_id' column.")


# Function to update the table
def update_table(data):
    try:
        # Connect to the database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Iterate through the DataFrame and update rows
        for _, row in data.iterrows():
            query = """
            UPDATE season_pitching_statistics
            SET hr_per_9 = %s,
                ld_percent = %s,
                gb_percent = %s,
                flyball_percent = %s
            WHERE row_id = %s;
            """
            cursor.execute(query, (
                row['HR/9'],        # Value for hr_per_9 column
                row['LD%'],         # Value for ld_percent column
                row['GB%'],         # Value for gb_percent column
                row['FB%'],         # Value for fb_percent column
                row['row_id']       # row_id as the primary key
            ))

        # Commit changes and close the connection
        conn.commit()
        cursor.close()
        conn.close()
        print("Table updated successfully.")

    except Exception as e:
        print(f"Error updating table: {e}")

# Main function
def main():
    # Path to the updated CSV file
    CSV_PATH = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/rowidseason_pitching_statistics.csv"

    # Load the CSV file into a Pandas DataFrame
    try:
        print("Loading CSV file...")
        data = pd.read_csv(CSV_PATH)
        print(f"Loaded {len(data)} rows from the CSV file.")
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        return

    # Check if the required columns exist in the CSV
    required_columns = ['row_id', 'HR/9', 'LOB%', 'LD%', 'GB%', 'FB%']
    for col in required_columns:
        if col not in data.columns:
            print(f"Missing required column in CSV: {col}")
            return

    # Update the database table
    print("Updating database table...")
    update_table(data)
    print("Update complete.")


if __name__ == "__main__":
    main()

