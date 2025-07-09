import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

def map_event_to_class(event):
    if event == "single":
        return "single"
    elif event in ["double", "triple", "home_run"]:
        return "extra_base_hit"
    elif event in ["walk", "hit_by_pitch"]:
        return "walk"
    elif event in ["strikeout", "strikeout_double_play"]:
        return "strikeout"
    else:
        return "out"

#create features to use in the models
def generate_features(df):

    df["outcome_class"] = df["events"].apply(map_event_to_class)

    #count during pitch sequence
    df["count"] = df["balls"].astype(str) + "-" + df["strikes"].astype(str)

    df["base_state"] = df.apply(
        lambda row: f"{int(pd.notna(row.on_1b))}{int(pd.notna(row.on_2b))}{int(pd.notna(row.on_3b))}", axis=1
    )

    # situation context
    df["inning"] = pd.to_numeric(df["inning"], errors="coerce")
    df["inning_topbot"] = df["inning_topbot"].astype(str).str.upper()
    df["stand"] = df["stand"].astype(str).str.upper()
    df["p_throws"] = df["p_throws"].astype(str).str.upper()

    # select necessary feature columns
    feature_cols = [
        "count", "base_state", "outs_when_up", "inning", "inning_topbot",
        "stand", "p_throws", "pitcher_id", "batter_id"
    ]
    df = df.dropna(subset=feature_cols + ["outcome_class"])

    return df[feature_cols + ["outcome_class"]].copy()

#encode categorical and numeric features
def encode_features(df):
    categorical_cols = ["count", "base_state", "inning_topbot", "stand", "p_throws"]
    numeric_cols = ["outs_when_up", "inning"]
    X = df[categorical_cols + numeric_cols]
    y = df["outcome_class"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_cols),
        ],
        remainder="passthrough"  # passthrough numeric cols
    )
    X_processed = preprocessor.fit_transform(X)

    return X_processed, y, preprocessor



if __name__ == "__main__":
    file_path = "/Users/joshsteckler/PycharmProjects/baseball-mvp/situation_game_probability/data/merged_statcast_2022_2024_with_stats.csv"
    df = pd.read_csv(file_path)

    # Create Features and Target Column
    df_cleaned = generate_features(df)
    output_clean_path = "/Users/joshsteckler/PycharmProjects/baseball-mvp/situation_game_probability/data/cleaned_features.csv"
    df_cleaned.to_csv(output_clean_path, index=False)
    print(f"Cleaned features saved to: {output_clean_path}")

    X, y, preprocessor = encode_features(df_cleaned)

    print("Features and target prepared.")
    print("Feature matrix shape:", X.shape)
    print("Target distribution:\n", y.value_counts(normalize=True))

