# train_random_forest.py
import pickle

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, log_loss, roc_auc_score, accuracy_score
from sklearn.preprocessing import LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
import os


DATA_DIR = "/Users/joshsteckler/PycharmProjects/baseball-mvp/situation_game_probability/data"

X_train = pd.read_csv(os.path.join(DATA_DIR, "X_train.csv"))
y_train = pd.read_csv(os.path.join(DATA_DIR, "y_train.csv")).squeeze()
X_val = pd.read_csv(os.path.join(DATA_DIR, "X_val.csv"))
y_val = pd.read_csv(os.path.join(DATA_DIR, "y_val.csv")).squeeze()
le = LabelEncoder()
y_train_enc = le.fit_transform(y_train)
y_val_enc = le.transform(y_val)

# --- Encode categorical features ---
categorical = ["count", "base_state", "inning_topbot", "stand", "p_throws"]
numeric = ["outs_when_up", "inning"]

preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical),
    ],
    remainder="passthrough"
)

X_train_encoded = preprocessor.fit_transform(X_train)
X_val_encoded = preprocessor.transform(X_val)

# Train model
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=None,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)
model.fit(X_train_encoded, y_train_enc)

# Predict and Evaluate Performance
y_val_pred = model.predict(X_val_encoded)
y_val_proba = model.predict_proba(X_val_encoded)

print("\nRandom Forest Validation Results:\n")
print("Log Loss:", round(log_loss(y_val_enc, y_val_proba), 4))
print("Classification Report:")
print(classification_report(y_val_enc, y_val_pred, target_names=le.classes_))

try:
    auc_score = roc_auc_score(y_val_enc, y_val_proba, multi_class="ovr")
    print(f"AUC (OvR): {round(auc_score, 4)}")
except:
    print("AUC computation failed.")

print("\nConfusion Matrix:")
print(confusion_matrix(y_val_enc, y_val_pred))

results = {
    "model": "Random Forest",
    "log_loss": log_loss(y_val_enc, y_val_proba),
    "accuracy": accuracy_score(y_val_enc, y_val_pred),
    "auc_ovr": auc_score,
    "y_true": y_val_enc.tolist(),        # ensure NumPy arrays become serializable
    "y_pred": y_val_pred.tolist(),
    "target_names": le.classes_.tolist()
}

with open(os.path.join(DATA_DIR, "results_random_forest.pkl"), "wb") as f:
    pickle.dump(results, f)

print("\n Results saved to results_random_forest.pkl")