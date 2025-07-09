import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, LabelEncoder
from sklearn.compose import ColumnTransformer
from sklearn.metrics import classification_report, log_loss, confusion_matrix, roc_auc_score
import os
from sklearn.metrics import accuracy_score
import pickle
DATA_DIR = "/Users/joshsteckler/PycharmProjects/baseball-mvp/situation_game_probability/data"

# Read data
X_train = pd.read_csv(os.path.join(DATA_DIR, "X_train.csv"))
y_train = pd.read_csv(os.path.join(DATA_DIR, "y_train.csv")).squeeze()
X_val = pd.read_csv(os.path.join(DATA_DIR, "X_val.csv"))
y_val = pd.read_csv(os.path.join(DATA_DIR, "y_val.csv")).squeeze()

# --- Encode and set columns
le = LabelEncoder()
y_train_enc = le.fit_transform(y_train)
y_val_enc = le.transform(y_val)
categorical = ["count", "base_state", "inning_topbot", "stand", "p_throws"]
numeric = ["outs_when_up", "inning"]

# Preprocess pipeline
preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ("num", StandardScaler(), numeric)
    ]
)

# model pipeline
model = Pipeline(steps=[
    ("preprocessing", preprocessor),
    ("classifier", LogisticRegression(
        penalty="elasticnet",
        solver="saga",
        l1_ratio=0.5,              # Blend of L1 (lasso) and L2 (ridge)
        class_weight="balanced",  # Handle class imbalance
        max_iter=1000,
        multi_class="multinomial",
        random_state=42
    ))
])

# Training model
model.fit(X_train, y_train_enc)
y_val_pred = model.predict(X_val)
y_val_proba = model.predict_proba(X_val)
print("Elastic Net Validation Results:\n")

print("Log Loss:", round(log_loss(y_val_enc, y_val_proba), 4))
print("\nClassification Report:")
print(classification_report(y_val_enc, y_val_pred, target_names=le.classes_))

try:
    auc_score = roc_auc_score(y_val_enc, y_val_proba, multi_class="ovr")
    print(f"AUC (OvR): {round(auc_score, 4)}")
except:
    print("AUC computation failed (class imbalance or label error).")


print("\nConfusion Matrix:")
print(confusion_matrix(y_val_enc, y_val_pred))

results = {
    "model": "Elastic Net",
    "log_loss": log_loss(y_val_enc, y_val_proba),
    "accuracy": accuracy_score(y_val_enc, y_val_pred),
    "auc_ovr": auc_score,
    "y_true": y_val_enc.tolist(),        # ensure NumPy arrays become serializable
    "y_pred": y_val_pred.tolist(),
    "target_names": le.classes_.tolist()
}

with open(os.path.join(DATA_DIR, "results_elastic_net_original.pkl"), "wb") as f:
    pickle.dump(results, f)

print("\n Results saved to results_elastic_net_original.pkl")
