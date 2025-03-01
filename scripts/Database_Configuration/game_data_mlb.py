import requests
import pandas as pd
import boto3
import os
from dotenv import load_dotenv

# Load environment variables (for S3 credentials)
load_dotenv()

# MLB API Endpoint
MLB_API_URL = "http://statsapi.mlb.com/api/v1/schedule/games/?sportId=1&startDate=2024-03-28&endDate=2024-09-29"


# Fetch game data
def fetch_mlb_game_data():
    response = requests.get(MLB_API_URL)

    if response.status_code != 200:
        print(f"Error: Failed to fetch game data (status {response.status_code})")
        return None

    data = response.json()

    # Extract game data
    games_list = []
    for date_info in data.get("dates", []):  # Loop through dates
        for game in date_info.get("games", []):  # Loop through games for each date
            games_list.append({
                "game_id": game.get("gamePk"),
                "game_date": game.get("gameDate"),
                "venue": game.get("venue", {}).get("name", "Unknown Venue"),
                "home_team_id": game.get("teams", {}).get("home", {}).get("team", {}).get("id"),
                "home_team": game.get("teams", {}).get("home", {}).get("team", {}).get("name"),
                "home_score": game.get("teams", {}).get("home", {}).get("score", None),  # Avoid KeyError
                "away_team_id": game.get("teams", {}).get("away", {}).get("team", {}).get("id"),
                "away_team": game.get("teams", {}).get("away", {}).get("team", {}).get("name"),
                "away_score": game.get("teams", {}).get("away", {}).get("score", None),  # Avoid KeyError
                "series_description": game.get("seriesDescription", "Unknown Series"),
            })

    # Convert to DataFrame
    game_df = pd.DataFrame(games_list)

    print(f"Retrieved {len(game_df)} games.")

    return game_df


# Save DataFrame to CSV
def save_to_csv(df, filename="mlb_game_data.csv"):
    if df is not None and not df.empty:
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
    else:
        print(" No data available to save.")


# Upload to S3
def upload_to_s3(file_path, bucket_name, s3_key):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    try:
        s3.upload_file(file_path, bucket_name, s3_key)
        print(f"File uploaded to S3: s3://{bucket_name}/{s3_key}")
    except Exception as e:
        print(f" Error uploading to S3: {e}")


# Main execution
if __name__ == "__main__":
    game_df = fetch_mlb_game_data()

    if game_df is not None:
        csv_filename = "mlb_game_data.csv"
        save_to_csv(game_df, csv_filename)

        # (Optional) Upload to S3
        S3_BUCKET_NAME = "baseball-data-mvp"
        S3_KEY = f"mlb_game_data/{csv_filename}"
        upload_to_s3(csv_filename, S3_BUCKET_NAME, S3_KEY)

