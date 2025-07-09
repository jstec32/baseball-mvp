import pandas as pd
from sklearn.model_selection import train_test_split
import os

# Config
DATA_DIR = "/Users/joshsteckler/PycharmProjects/baseball-mvp/situation_game_probability/data"
CLEANED_FEATURES_FILE = os.path.join(DATA_DIR, "cleaned_features.csv")

def load_feature_data(path):
    return pd.read_csv(path)

def stratified_split(df, target_col="outcome_class", test_size=0.15, val_size=0.15):
    X = df.drop(columns=[target_col])
    y = df[target_col]


    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=(test_size + val_size), stratify=y, random_state=42
    )


    val_frac = val_size / (test_size + val_size)
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=val_frac, stratify=y_temp, random_state=42
    )

    return X_train, y_train, X_val, y_val, X_test, y_test

if __name__ == "__main__":
    df = load_feature_data(CLEANED_FEATURES_FILE)

    X_train, y_train, X_val, y_val, X_test, y_test = stratified_split(df)


    X_train.to_csv(os.path.join(DATA_DIR, "X_train.csv"), index=False)
    y_train.to_csv(os.path.join(DATA_DIR, "y_train.csv"), index=False)
    X_val.to_csv(os.path.join(DATA_DIR, "X_val.csv"), index=False)
    y_val.to_csv(os.path.join(DATA_DIR, "y_val.csv"), index=False)
    X_test.to_csv(os.path.join(DATA_DIR, "X_test.csv"), index=False)
    y_test.to_csv(os.path.join(DATA_DIR, "y_test.csv"), index=False)

    print("Train/Val/Test splits saved to:")
    print(DATA_DIR)
