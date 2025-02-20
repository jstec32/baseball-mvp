import os
import joblib
import boto3
import pandas as pd
import numpy as np
import glob
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, MinMaxScaler

# Load .env
load_dotenv()

# Retrieve AWS credentials and S3 details
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_FOLDER_NAME = "model_training_data"
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432))  # Default port 5432 if not set
}
# Ensure all required environment variables are set
if not all([S3_BUCKET_NAME, S3_FOLDER_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY]):
    raise ValueError("Missing AWS credentials or S3 settings in .env file!")

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# Load only 1 season of data (latest available)
data_dir = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/S3_Data"
csv_files = sorted(glob.glob(os.path.join(data_dir, "statcast_data_2024_*.csv")), reverse=True)


combined_data = pd.DataFrame()

for file in csv_files:
    print(f"Processing file: {file}...")
    try:
        data_chunk = pd.read_csv(file, low_memory=False)
        combined_data = pd.concat([combined_data, data_chunk], ignore_index=True)
    except Exception as e:
        print(f" Error loading {file}: {e}")

print(f"Combined dataset shape: {combined_data.shape}")
import psycopg2
import pandas as pd
import numpy as np

# Connect to PostgreSQL
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # SQL query to get hitter season statistics (Make sure 'name' is returned explicitly)
    SQL_QUERY = """
    WITH players_with_team AS (
    SELECT 
        p.key_mlbam AS batter_id,  
        CONCAT(p."First_Name", ' ', p."Last_Name") AS name
    FROM players p
),
most_recent_season AS (
    SELECT MAX(season) AS season
    FROM hitter_season_statistics
)
SELECT 
    pwt.batter_id,
    hs.team,  -- Include team for encoding
    hs.batting_average AS ba,
    hs.ops,
    hs.ld_percent,
    hs.gb_percent,
    hs.fb_percent,
    hs.bb_percent,
    hs.k_percent
FROM hitter_season_statistics hs
JOIN players_with_team pwt
    ON pwt.name = hs.name
JOIN most_recent_season mrs
    ON hs.season = mrs.season;
    """

    # Fetch Data
    cursor.execute(SQL_QUERY)
    columns = [desc[0] for desc in cursor.description]  # Extract column names
    hitter_stats = pd.DataFrame(cursor.fetchall(), columns=columns)

    # Close connection
    cursor.close()
    conn.close()

    print(f" Hitter stats fetched. Shape: {hitter_stats.shape}")

except Exception as e:
    print(f" Error fetching hitter stats: {e}")
    hitter_stats = pd.DataFrame()  # Ensure script continues even if fetching fails

# Ensure batter_id is treated as a string for merging compatibility
hitter_stats["batter_id"] = hitter_stats["batter_id"].astype(str)
combined_data["batter_id"] = combined_data["batter_id"].astype(str)

# Merge Statcast Data with Hitter Stats
if not hitter_stats.empty:
    combined_data = combined_data.merge(hitter_stats, on="batter_id", how="left")
    print(" Hitter season stats merged with Statcast data.")
else:
    print(" Skipping hitter stats merge due to missing data.")

# Ensure team column exists
if not hitter_stats.empty:
    combined_data = combined_data.merge(hitter_stats, on="batter_id", how="left")
    print(" Hitter season stats merged with Statcast data.")

    # Ensure 'team' column exists after merging
    if "team" in combined_data.columns:
        le = LabelEncoder()
        combined_data["team_encoded"] = le.fit_transform(combined_data["team"])
        print(" Team column encoded with Label Encoding.")

        # Drop original team acronym column after encoding
        combined_data.drop(columns=["team"], inplace=True)
    else:
        print("  Warning: 'team' column not found in combined_data!")
# Ensure the models directory exists
os.makedirs("models", exist_ok=True)

# STEP 1: Define Pitch Type Mapping (Must be done first)
pitch_type_mapping = {
    "CH": "CH", "FF": "FF", "SI": "SI", "SL": "SL", "ST": "ST", "FC": "FC",
    "CB": ["CU", "KC"], "Other": ["EP", "FO", "KN", "SC", "SV", "FA", "PO", "CS"]
}

def map_pitch_type(pitch):
    for key, values in pitch_type_mapping.items():
        if isinstance(values, list) and pitch in values:
            return key
        elif pitch == values:
            return key
    return "Other"

combined_data["pitch_type_grouped"] = combined_data["pitch_type"].apply(map_pitch_type)
encoder = LabelEncoder()
combined_data["pitch_type_encoded"] = encoder.fit_transform(combined_data["pitch_type_grouped"])
joblib.dump(encoder, "models/pitch_type_encoder.pkl")

# STEP 2: Game Context Features (Ensure they exist before shifting)
combined_data["runners_on"] = (combined_data["on_1b"].fillna(0) + combined_data["on_2b"].fillna(0) + combined_data["on_3b"].fillna(0)) > 0
combined_data["outs_remaining"] = 3 - combined_data["outs_when_up"].fillna(0)
combined_data["late_game"] = (combined_data["inning"].fillna(0) >= 7).astype(int)

combined_data["high_leverage_score"] = (
    (combined_data["runners_on"].astype(int) * 1.5) +
    ((3 - combined_data["outs_when_up"].fillna(0)) * 1.2) +
    (combined_data["late_game"] * 1.3)
)
combined_data["high_leverage_situation"] = (combined_data["runners_on"] & (combined_data["outs_when_up"].fillna(0) < 2)).astype(int)

# STEP 3: Encode Previous Pitch Features (After `pitch_type_encoded` exists)
for i in range(1, 5):
    combined_data[f"previous_pitch_{i}"] = combined_data.groupby("game_id")["pitch_type_encoded"].shift(i).fillna(-1).astype(int)

encoder.fit(pd.concat([combined_data[f"previous_pitch_{i}"] for i in range(1, 5)]))
for i in range(1, 5):
    combined_data[f"previous_pitch_{i}_encoded"] = encoder.transform(combined_data[f"previous_pitch_{i}"])

# STEP 4: Classify Previous Pitch Outcome
def classify_pitch_outcome(outcome):
    if outcome in {"called_strike", "swinging_strike", "swinging_strike_blocked"}:
        return "Strike"
    elif outcome in {"foul", "foul_tip", "foul_bunt"}:
        return "Foul"
    elif outcome in {"ball", "blocked_ball", "pitchout"}:
        return "Ball"
    elif outcome in {"hit_into_play"}:
        return "Batted_Ball"
    elif outcome in {"hit_by_pitch"}:
        return "Batter_Advances"
    elif outcome in {"missed_bunt"}:
        return "Missed_Bunt"
    return "Other"

combined_data["prev_pitch_outcome_grouped"] = combined_data["description"].apply(classify_pitch_outcome)
combined_data["prev_pitch_outcome_grouped"] = combined_data.groupby("game_id")["prev_pitch_outcome_grouped"].shift(1).fillna("Other")
encoder = LabelEncoder()
combined_data["prev_pitch_outcome_encoded"] = encoder.fit_transform(combined_data["prev_pitch_outcome_grouped"])
joblib.dump(encoder, "models/prev_pitch_outcome_encoder.pkl")

# STEP 5: Fix Rolling Pitch Frequency Calculation
combined_data["rolling_pitch_freq"] = (
    combined_data.groupby(["game_id", "pitcher_id", "pitch_type_encoded"]).cumcount() + 1
)
# Compute batter's rolling batting average (last 10 plate appearances with a hit)
hit_events = ["single", "double", "triple", "home_run"]

# Ensure 'events' exists in the dataset before applying the rolling function
if "events" in combined_data.columns:
    combined_data["batter_rolling_avg"] = (
        combined_data.groupby("batter_id")["events"]
        .apply(lambda x: x.isin(hit_events).rolling(10, min_periods=1).mean())
        .reset_index(level=0, drop=True)  # Align index
    )

    # Fill missing values in case some batters do not have 10 appearances
    combined_data["batter_rolling_avg"] = combined_data["batter_rolling_avg"].fillna(0)
    print(" 'batter_rolling_avg' calculated and missing values handled.")
else:
    print(" Warning: 'events' column not found. 'batter_rolling_avg' will not be included.")
# Encode pitcher and batter handedness
if "p_throws" in combined_data.columns and "stand" in combined_data.columns:
    combined_data["pitcher_hand_encoded"] = combined_data["p_throws"].map({"L": 0, "R": 1})
    combined_data["batter_hand_encoded"] = combined_data["stand"].map({"L": 0, "R": 1})

    # Drop the original categorical columns after encoding
    combined_data.drop(columns=["p_throws", "stand"], errors="ignore", inplace=True)

scaler = MinMaxScaler()
combined_data[["rolling_pitch_freq", "high_leverage_score", "batter_rolling_avg"]] = scaler.fit_transform(
    combined_data[["rolling_pitch_freq", "high_leverage_score", "batter_rolling_avg"]]
)

# Log transform rolling pitch frequency to normalize distribution
combined_data["log_rolling_pitch_freq"] = np.log1p(combined_data["rolling_pitch_freq"])

# Ensure 'count' column exists before processing
if "count" in combined_data.columns:
    # Convert count to string for consistency
    combined_data["count"] = combined_data["count"].astype(str)


    def adjust_count(count):
        """Adjusts invalid counts to the highest valid baseball count."""
        try:
            balls, strikes = map(int, count.split("-"))

            # Cap max balls at 4
            if balls > 4:
                balls = 4

            # Cap max strikes at 2 (except full count of 3-2)
            if strikes > 2:
                strikes = 2 if balls < 3 else 3  # Keep "3-2" as a valid full count

            return f"{balls}-{strikes}"

        except ValueError:
            return "0-0"  # Default to 0-0 if parsing fails


    # Apply the adjustment function
    combined_data["count"] = combined_data["count"].apply(adjust_count)

    # Ordinal encoding of count instead of one-hot encoding
    count_mapping = {
        "0-0": 0, "0-1": 1, "0-2": 2, "1-0": 3, "1-1": 4, "1-2": 5,
        "2-0": 6, "2-1": 7, "2-2": 8, "3-0": 9, "3-1": 10, "3-2": 11,
        "4-0": 12, "4-1": 13, "4-2": 14
    }

    combined_data["count_encoded"] = combined_data["count"].map(count_mapping).fillna(0).astype(int)
    # Create interaction features
    combined_data["pitch_1_count_interaction"] = combined_data["previous_pitch_1_encoded"] * combined_data[
        "count_encoded"]
    combined_data["pitcher_batter_matchup"] = combined_data["pitcher_hand_encoded"] * combined_data[
        "batter_hand_encoded"]

    print(" Ordinal encoding applied to 'count' column with adjusted counts.")

    # Drop the original count column after encoding
    combined_data.drop(columns=["count"], inplace=True)
else:
    print("Warning: 'count' column not found in dataset. Skipping encoding.")

# STEP 6: Sample Data for Quick Analysis
sampled_data = combined_data.sample(n=10000, random_state=42)
sampled_data.to_csv(os.path.join(data_dir, "Sampled_Data.csv"), index=False)

# STEP 7: Ensure Required Features Exist Before Train-Test Split
features = [
    # Game Context Features
    "inning", "runners_on", "outs_remaining", "high_leverage_situation", "high_leverage_score", "late_game",

    # Rolling Frequency & Outcome Features
    "rolling_pitch_freq", "log_rolling_pitch_freq", "prev_pitch_outcome_encoded", "batter_rolling_avg",

    # Previous Pitch Encoding
    "previous_pitch_1_encoded", "previous_pitch_2_encoded",
    "previous_pitch_3_encoded", "previous_pitch_4_encoded",

    # Pitcher & Batter Matchup Features
    "pitcher_hand_encoded", "batter_hand_encoded", "pitcher_batter_matchup",

    # Count Features
    "count_encoded", "count_0-0",

    # Team & Player Performance Metrics
    "team_encoded", "batting_average", "on_base_percentage", "slugging_percentage", "ops",
    "wrc_plus", "iso", "babip", "ld_percent", "gb_percent", "fb_percent", "hard_hit_percent",

    # Interaction Features
    "pitch_1_count_interaction"
]

available_features = [col for col in features if col in combined_data.columns]

# Train-Test Split
train_data, test_data = train_test_split(
    combined_data[available_features + ["pitch_type_encoded"]],
    test_size=0.3,
    shuffle=True,
    random_state=42,
    stratify=combined_data["pitch_type_encoded"]
)

# Save locally
train_file = "Train_ModelB.csv"
test_file = "Test_ModelB.csv"
train_data.to_csv(train_file, index=False)
test_data.to_csv(test_file, index=False)

# Upload to S3
s3_client.upload_file(train_file, S3_BUCKET_NAME, f"{S3_FOLDER_NAME}/{train_file}")
s3_client.upload_file(test_file, S3_BUCKET_NAME, f"{S3_FOLDER_NAME}/{test_file}")

print(" Feature Engineering Complete. Data Uploaded to S3.")
