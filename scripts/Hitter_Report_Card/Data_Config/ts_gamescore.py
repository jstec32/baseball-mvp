import boto3
import pandas as pd
import os
from io import StringIO
from dotenv import load_dotenv

# Load AWS credentials
load_dotenv()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = "baseball-data-mvp"
MERGED_KEY = "mlb_game_data/merged_pitch_box_scores_2025.csv"  # Update to 2025 when ready

def get_game_score_from_s3(game_id, batter_id):
    """Loads merged game data from S3 and returns scaled game score for one hitter/game."""
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )

        response = s3.get_object(Bucket=AWS_BUCKET_NAME, Key=MERGED_KEY)
        df = pd.read_csv(StringIO(response["Body"].read().decode("utf-8")))

        df["game_id"] = df["game_id"].astype(int)
        df["batter_id"] = df["batter_id"].astype(int)

        row = df[(df["game_id"] == game_id) & (df["batter_id"] == batter_id)]
        if not row.empty:
            return round(row.iloc[0]["scaled_game_score"], 1)
        else:
            print("⚠️ No match found for game_id and batter_id.")
            return None

    except Exception as e:
        print(f"❌ Error loading game score: {e}")
        return None


# ------------------------------
# 🔧 TEST SECTION
# Replace with known values from your data
test_game_id = '744795'         # Example game_id
test_batter_id = '493329'       # Example batter_id

score = get_game_score_from_s3(test_game_id, test_batter_id)

if score is not None:
    print(f"✅ Game Score for batter {test_batter_id} in game {test_game_id}: {score}")
else:
    print("❌ Could not retrieve game score.")
