# Import necessary libraries
import os

import boto3
import pandas as pd
import numpy as np
from io import StringIO
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split

# Load environment variables
load_dotenv()

# AWS Credentials
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = "baseball-data-mvp"
MLB_GAME_DATA_PATH = "mlb_game_data/merged_pitch_box_scores_2024.csv"

# Function to load dataset from S3
def load_box_scores_from_s3():
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
    try:
        response = s3_client.get_object(Bucket=AWS_BUCKET_NAME, Key=MLB_GAME_DATA_PATH)
        csv_content = response['Body'].read().decode('utf-8')
        box_scores_df = pd.read_csv(StringIO(csv_content))
        print(f"Loaded {len(box_scores_df)} game records from S3.")
        return box_scores_df

    except Exception as e:
        print(f"Error fetching box scores from S3: {e}")
        return None

# Load dataset
final_data = load_box_scores_from_s3()

# Ensure data is loaded
if final_data is not None:
    # Split dataset into training (70%) and validation (30%)
    train_df, val_df = train_test_split(final_data, test_size=0.3, random_state=42)

    # Save split datasets for future tuning
    train_csv_path = "train_hitter_game_scores.csv"
    val_csv_path = "val_hitter_game_scores.csv"

    train_df.to_csv(train_csv_path, index=False)
    val_df.to_csv(val_csv_path, index=False)

    print(f"Training set saved to: {train_csv_path}")
    print(f"Validation set saved to: {val_csv_path}")

# Function to compute game score
def compute_hitter_game_score(df, weights):
    # Define weight ranges for tuning

    df["game_score"] = 50  # Base score

    df["game_score"] += (df["hits"] - df["doubles"] - df["triples"] - df["homeRuns"]) * weights["1B"]
    df["game_score"] += df["doubles"] * weights["2B"]
    df["game_score"] += df["triples"] * weights["3B"]
    df["game_score"] += df["homeRuns"] * weights["HR"]
    df["game_score"] += df["rbi"] * weights["RBI"]
    df["game_score"] += df["runs"] * weights["Runs"]
    df["game_score"] += df["baseOnBalls"] * weights["BB"]
    df["game_score"] -= df["strikeOuts"] * weights["K"]
    df["game_score"] -= df["groundIntoDoublePlay"] * weights["GIDP"]
    df["game_score"] += df["sacFlies"] * weights["Sac"]
    df["game_score"] += df["stolenBases"] * weights["SB"]
    df["game_score"] -= df["caughtStealing"] * weights["CS"]
    df["game_score"] += df["total_barrels"] * weights["Barrels"]
    df["game_score"] += (df["avg_exit_velocity"] - 90) * weights["Exit Velocity"]
    df["game_score"] += df["total_delta_run_exp"] * weights["Delta RE"]

    return df


weight_options = {
        "1B": [3, 4, 5],
        "2B": [5, 6, 7],
        "3B": [7, 8, 9],
        "HR": [10, 12, 15],
        "RBI": [1, 2, 3],
        "Runs": [1, 2, 3],
        "BB": [1, 2, 3],
        "K": [1, 2, 3],
        "GIDP": [2, 3, 4],
        "Sac": [1, 2],
        "SB": [2, 3],
        "CS": [2, 3],
        "Barrels": [5, 6, 7],
        "Exit Velocity": [0.4, 0.5, 0.6],
        "Delta RE": [8, 10, 12]
    }


def calculate_wOBA(df):
    """ Compute wOBA for each player in each game using 2024 weights. """

    # Ensure column names are correct
    expected_columns = ["baseOnBalls", "hitByPitch", "hits", "doubles", "triples",
                        "homeRuns", "atBats", "sacFlies"]

    for col in expected_columns:
        if col not in df.columns:
            raise KeyError(f"Missing expected column: {col}")

    # Convert necessary columns to numeric (fixes 'Series' object error)
    for col in expected_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Define 2024 wOBA weights
    wOBA_weights = {
        "BB": 0.689,   # Unintentional Walks
        "HBP": 0.720,  # Hit by Pitch
        "1B": 0.882,   # Singles (Hits - Extra Base Hits)
        "2B": 1.254,   # Doubles
        "3B": 1.590,   # Triples
        "HR": 2.050    # Home Runs
    }

    # Compute numerator (weighted sum of offensive events)
    df["wOBA_numerator"] = (
        (df["baseOnBalls"] * wOBA_weights["BB"]) +
        (df["hitByPitch"] * wOBA_weights["HBP"]) +
        ((df["hits"] - df["doubles"] - df["triples"] - df["homeRuns"]) * wOBA_weights["1B"]) +
        (df["doubles"] * wOBA_weights["2B"]) +
        (df["triples"] * wOBA_weights["3B"]) +
        (df["homeRuns"] * wOBA_weights["HR"])
    )

    # Compute denominator (plate appearances that count for wOBA)
    df["wOBA_denominator"] = (
        df["atBats"] + df["baseOnBalls"] - df["sacFlies"] + df["hitByPitch"]
    )

    # Avoid division by zero (replace NaN with 0)
    df["wOBA"] = df["wOBA_numerator"] / df["wOBA_denominator"]
    df["wOBA"] = df["wOBA"].fillna(0)  # Replace NaN values with 0 for players with no qualifying PAs

    return df



# Apply wOBA calculation
final_data = calculate_wOBA(final_data)


# Function to tune game score
def tune_game_score(train_df, val_df):
    best_score = float('-inf')
    best_weights = None
    default_weights = {
        "1B": 4, "2B": 6, "3B": 8, "HR": 12, "RBI": 2, "Runs": 2, "BB": 1,
        "K": 2, "GIDP": 3, "Sac": 1, "SB": 2, "CS": 2, "Barrels": 6,
        "Exit Velocity": 0.5, "Delta RE": 10
    }

    for _ in range(30):  # Test 30 random weight combinations
        test_weights = {k: np.random.choice(v) for k, v in weight_options.items()}

        # Compute Game Score with the current weight set
        tuned_train_df = compute_hitter_game_score(train_df.copy(), test_weights)
        tuned_val_df = compute_hitter_game_score(val_df.copy(), test_weights)

        # Evaluate Performance
        avg_val_score = tuned_val_df["game_score"].mean()
        std_dev = tuned_val_df["game_score"].std()

        # Choose the weight set with high avg score & small std deviation
        if avg_val_score > best_score and std_dev < 10:
            best_score = avg_val_score
            best_weights = test_weights

    # Ensure we return at least some weights
    return best_weights if best_weights else default_weights


# Run weight tuning
best_weights = tune_game_score(train_df, val_df)

# Apply the best weights and compute final scores
final_data = compute_hitter_game_score(final_data, best_weights)

# Save final tuned game scores
final_csv_path = "final_tuned_hitter_game_scores.csv"
final_data.to_csv(final_csv_path, index=False)
print(f"Saved final tuned Game Score dataset to {final_csv_path}")

import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr

# Scatter plot of Game Score vs. wOBA
plt.figure(figsize=(8,6))
sns.scatterplot(x=final_data["wOBA"], y=final_data["game_score"])
plt.xlabel("wOBA")
plt.ylabel("Game Score")
plt.title("Comparison of wOBA vs. Game Score")
plt.show()

valid_data = final_data[["wOBA", "game_score"]].replace([np.inf, -np.inf], np.nan).dropna()

# Check if there's enough data to compute correlation
if len(valid_data) > 0:
    correlation, _ = pearsonr(valid_data["wOBA"], valid_data["game_score"])
    print(f"Pearson Correlation between wOBA and Game Score: {correlation:.3f}")
else:
    print("Not enough valid data to compute correlation.")

# Check basic stats
print("Game Score Summary:")
print(final_data["game_score"].describe())

# Optional: visualize
import matplotlib.pyplot as plt

plt.hist(final_data["game_score"], bins=50, color="skyblue", edgecolor="black")
plt.axvline(final_data["game_score"].median(), color="red", linestyle="--", label="Median (P50)")
plt.title("Distribution of Hitter Game Scores")
plt.xlabel("Game Score")
plt.ylabel("Frequency")
plt.legend()
plt.show()

# Create Plate Appearances column
final_data["plate_appearances"] = (
    final_data["atBats"] + final_data["baseOnBalls"] +
    final_data["hitByPitch"] + final_data["sacFlies"] + final_data["sacBunts"]
)

# Avoid divide-by-zero
final_data["plate_appearances"] = final_data["plate_appearances"].replace(0, np.nan)

# Game Score per PA (rate version)
final_data["game_score_per_pa"] = final_data["game_score"] / final_data["plate_appearances"]

features = [
    "hits", "doubles", "triples", "homeRuns", "rbi", "runs",
    "baseOnBalls", "hitByPitch", "strikeOuts", "groundIntoDoublePlay",
    "sacFlies", "stolenBases", "caughtStealing",
    "total_barrels", "avg_exit_velocity", "total_delta_run_exp"
]

# Filter and clean
model_df = final_data.dropna(subset=["wOBA", "plate_appearances"])
# Drop invalid values from both X and y
model_df = model_df.replace([np.inf, -np.inf], np.nan).dropna(subset=["wOBA"] + features)

X = model_df[features]
y = model_df["wOBA"]

from sklearn.linear_model import LinearRegression

model = LinearRegression()
model.fit(X, y)

# Store coefficients as a new dictionary of learned weights
learned_weights = dict(zip(features, model.coef_))

print("📊 Learned Weights Based on wOBA:\n")
for k, v in learned_weights.items():
    print(f"{k}: {v:.4f}")

# Apply new Game Score calculation
def compute_regression_game_score(df, weights):
    df["regression_game_score"] = 50  # Start baseline

    for feature, weight in weights.items():
        df["regression_game_score"] += df[feature] * weight

    return df

# Recalculate game scores
final_data = compute_regression_game_score(final_data, learned_weights)

from scipy.stats import pearsonr

valid = final_data[["regression_game_score", "wOBA"]].replace([np.inf, -np.inf], np.nan).dropna()
corr, _ = pearsonr(valid["regression_game_score"], valid["wOBA"])

print(f"📈 Pearson Correlation (wOBA vs Regression-Based Game Score): {corr:.3f}")

import matplotlib.pyplot as plt
import seaborn as sns

# Use your learned weights
weights = {
    "hits": 0.1822,
    "doubles": 0.0968,
    "triples": 0.1849,
    "homeRuns": 0.3232,
    "rbi": -0.0300,
    "runs": -0.0181,
    "baseOnBalls": 0.1241,
    "hitByPitch": 0.1375,
    "strikeOuts": -0.0281,
    "groundIntoDoublePlay": -0.0229,
    "sacFlies": 0.1891,
    "stolenBases": -0.0032,
    "caughtStealing": 0.0085,
    "total_barrels": -0.0209,
    "avg_exit_velocity": 0.0012,
    "total_delta_run_exp": 0.0306
}

# Apply weights to calculate new regression-based Game Score
def compute_game_score(df, weights):
    df["regression_game_score"] = 50  # Start from base score
    for stat, weight in weights.items():
        if stat in df.columns:
            df["regression_game_score"] += df[stat] * weight
    return df

# Apply to your final_data
final_data = compute_game_score(final_data, weights)

# Plot Game Score vs. wOBA
plt.figure(figsize=(8, 6))
sns.scatterplot(x=final_data["wOBA"], y=final_data["regression_game_score"])
plt.xlabel("wOBA")
plt.ylabel("Regression-Based Game Score")
plt.title("Comparison of wOBA vs. Regression-Based Game Score")
plt.grid(True)
plt.show()

# 1. Get mean and standard deviation of the regression scores
mean_score = final_data["regression_game_score"].mean()
std_score = final_data["regression_game_score"].std()

# 2. Create new normalized game score with baseline 100
final_data["scaled_game_score"] = (
    ((final_data["regression_game_score"] - mean_score) / std_score) * 10
) + 100

final_data["scaled_game_score"] = final_data["scaled_game_score"].round(1)

import matplotlib.pyplot as plt

plt.figure(figsize=(10, 6))
plt.hist(final_data["scaled_game_score"], bins=50, color="mediumseagreen", edgecolor="black")
plt.axvline(100, color="red", linestyle="--", label="Average (100)")
plt.title("Distribution of Scaled Hitter Game Scores (Mean = 100)")
plt.xlabel("Scaled Game Score")
plt.ylabel("Frequency")
plt.legend()
plt.grid(True)
plt.show()

