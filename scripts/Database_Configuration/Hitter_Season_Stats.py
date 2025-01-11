import pandas as pd
from pybaseball import batting_stats
import psycopg2

# Database configuration
DB_CONFIG = {
    "host": "aws-0-us-east-2.pooler.supabase.com",
    "database": "postgres",
    "user": "postgres.chcovbrcpmlxyauansqe",
    "password": "1Z4IO6fxxYw8PgxL",
    "port": 5432
}


# Fetch hitter stats from pybaseball
def fetch_hitter_stats(start_year, end_year, qual=50):
    all_data = []
    for year in range(start_year, end_year + 1):
        print(f"Fetching hitting stats for the {year} season...")
        data = batting_stats(year, qual=qual)
        data['Season'] = year
        all_data.append(data)
    return pd.concat(all_data, ignore_index=True)


# Filter columns to match table schema
def filter_columns(data):
    columns_to_keep = {
        "IDfg": "idfg",
        "Season": "season",
        "Name": "name",
        "Team": "team",
        "Age": "age",
        "G": "games",
        "PA": "plate_appearances",
        "AB": "at_bats",
        "H": "hits",
        "2B": "doubles",
        "3B": "triples",
        "HR": "home_runs",
        "R": "runs",
        "RBI": "rbi",
        "BB%": "bb_percent",
        "K%": "k_percent",
        "BB": "walks",
        "SO": "strikeouts",
        "SB": "stolen_bases",
        "CS": "caught_stealing",
        "AVG": "batting_average",
        "OBP": "on_base_percentage",
        "SLG": "slugging_percentage",
        "OPS": "ops",
        "wRC+": "wrc_plus",
        "ISO": "iso",
        "BABIP": "babip",
        "LD%": "ld_percent",
        "GB%": "gb_percent",
        "FB%": "fb_percent",
        "HardHit%": "hard_hit_percent"
    }
    filtered_data = data[list(columns_to_keep.keys())]
    filtered_data.rename(columns=columns_to_keep, inplace=True)
    return filtered_data


# Save data to a CSV file
def save_to_csv(data, file_path):
    data.to_csv(file_path, index=False)
    print(f"Data saved to {file_path}")


# Insert data into PostgreSQL
def insert_data_to_db(data):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        for _, row in data.iterrows():
            query = """
            INSERT INTO hitter_season_statistics (
                idfg, season, name, team, age, games, plate_appearances, at_bats, hits, doubles,
                triples, home_runs, runs, rbi, walks, strikeouts, stolen_bases, caught_stealing,
                batting_average, on_base_percentage, slugging_percentage, ops, wrc_plus, iso,
                babip, ld_percent, gb_percent, fb_percent, hard_hit_percent
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, tuple(row))

        conn.commit()
        cursor.close()
        conn.close()
        print("Data inserted into database successfully.")
    except Exception as e:
        print(f"Error inserting data: {e}")


# Main function
def main():
    output_csv_path = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/hitter_season_statistics.csv"

    # Fetch data
    hitter_data = fetch_hitter_stats(2020, 2023, qual=50)

    # Filter data
    filtered_data = filter_columns(hitter_data)

    # Save to CSV
    save_to_csv(filtered_data, output_csv_path)

    # Insert into database
    insert_data_to_db(filtered_data)


if __name__ == "__main__":
    main()


