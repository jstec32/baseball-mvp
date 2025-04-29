import pandas as pd
from dotenv import load_dotenv
from pybaseball import batting_stats
import psycopg2

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


# Fetch hitter stats from pybaseball
def fetch_hitter_stats(start_year, end_year, qual=50):
    all_data = []
    for year in range(start_year, end_year + 1):
        print(f"Fetching hitting stats for the {year} season...")
        data = batting_stats(year, qual=qual)
        data['Season'] = year
        all_data.append(data)
        print(data.columns)
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


def insert_data_to_db(data):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        columns = [
            "idfg", "season", "name", "team", "age", "games", "plate_appearances", "at_bats", "hits", "doubles",
            "triples", "home_runs", "runs", "rbi","bb_percent", "k_percent", "walks", "strikeouts", "stolen_bases", "caught_stealing",
            "batting_average", "on_base_percentage", "slugging_percentage", "ops", "wrc_plus", "iso",
            "babip", "ld_percent", "gb_percent", "fb_percent", "hard_hit_percent"
        ]

        for _, row in data[columns].iterrows():
            query = """
            INSERT INTO hitter_season_statistics (
                idfg, season, name, team, age, games, plate_appearances, at_bats, hits, doubles,
                triples, home_runs, runs, rbi,bb_percent,k_percent, walks, strikeouts, stolen_bases, caught_stealing,
                batting_average, on_base_percentage, slugging_percentage, ops, wrc_plus, iso,
                babip, ld_percent, gb_percent, fb_percent, hard_hit_percent
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s)
            ON CONFLICT (idfg, season) DO UPDATE SET
                name = EXCLUDED.name,
                team = EXCLUDED.team,
                age = EXCLUDED.age,
                games = EXCLUDED.games,
                plate_appearances = EXCLUDED.plate_appearances,
                at_bats = EXCLUDED.at_bats,
                hits = EXCLUDED.hits,
                doubles = EXCLUDED.doubles,
                triples = EXCLUDED.triples,
                home_runs = EXCLUDED.home_runs,
                runs = EXCLUDED.runs,
                rbi = EXCLUDED.rbi,
                bb_percent = EXCLUDED.bb_percent,
                k_percent = EXCLUDED.k_percent,
                walks = EXCLUDED.walks,
                strikeouts = EXCLUDED.strikeouts,
                stolen_bases = EXCLUDED.stolen_bases,
                caught_stealing = EXCLUDED.caught_stealing,
                batting_average = EXCLUDED.batting_average,
                on_base_percentage = EXCLUDED.on_base_percentage,
                slugging_percentage = EXCLUDED.slugging_percentage,
                ops = EXCLUDED.ops,
                wrc_plus = EXCLUDED.wrc_plus,
                iso = EXCLUDED.iso,
                babip = EXCLUDED.babip,
                ld_percent = EXCLUDED.ld_percent,
                gb_percent = EXCLUDED.gb_percent,
                fb_percent = EXCLUDED.fb_percent,
                hard_hit_percent = EXCLUDED.hard_hit_percent
            ;
            """
            cursor.execute(query, tuple(row))

        conn.commit()
        cursor.close()
        conn.close()
        print("Hitter season stats upserted successfully.")
    except Exception as e:
        print(f"Error inserting data: {e}")



# Main function
def main_hitter_season_stats():
    output_csv_path = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/hitter_season_statistics_2024.csv"

    # grab data, filter, then save
    hitter_data = fetch_hitter_stats(2025, 2025, qual=1)
    filtered_data = filter_columns(hitter_data)
    save_to_csv(filtered_data, output_csv_path)
    insert_data_to_db(filtered_data)


if __name__ == "__main__":
    main_hitter_season_stats()


