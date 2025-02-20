import os
import joblib
import boto3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier
from sklearn.inspection import permutation_importance

# Load .env
load_dotenv()

# Retrieve AWS credentials and S3 details
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_FOLDER_NAME = "model_training_data"
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Ensure all required environment variables are set
if not all([S3_BUCKET_NAME, S3_FOLDER_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY]):
    raise ValueError("Missing AWS credentials or S3 settings in .env file!")

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# Local directory to store data
local_data_dir = "/tmp/baseball_data"
os.makedirs(local_data_dir, exist_ok=True)

# Define dataset paths in S3
train_file = f"{S3_FOLDER_NAME}/Train_ModelB.csv"
test_file = f"{S3_FOLDER_NAME}/Test_ModelB.csv"

# Download datasets from S3
local_train_file = os.path.join(local_data_dir, "Train_ModelB.csv")
local_test_file = os.path.join(local_data_dir, "Test_ModelB.csv")

s3_client.download_file(S3_BUCKET_NAME, train_file, local_train_file)
s3_client.download_file(S3_BUCKET_NAME, test_file, local_test_file)
print(f" Downloaded training and test datasets from S3.")

# Load the dataset
train_data = pd.read_csv(local_train_file)
test_data = pd.read_csv(local_test_file)

# Separate features (X) and target (y)
X_train = train_data.drop(columns=["pitch_type_encoded"])
y_train = train_data["pitch_type_encoded"]
X_test = test_data.drop(columns=["pitch_type_encoded"])
y_test = test_data["pitch_type_encoded"]

# Encode labels
label_encoder = LabelEncoder()
y_train = label_encoder.fit_transform(y_train)
y_test = label_encoder.transform(y_test)

# Identify categorical features (do not scale these)
categorical_features = ["pitcher_hand_encoded", "batter_hand_encoded", "team_encoded", "count_encoded",
                        "previous_pitch_1_encoded", "previous_pitch_2_encoded",
                        "previous_pitch_3_encoded", "previous_pitch_4_encoded"]

# Identify numerical features (to be scaled)
numerical_features = [col for col in X_train.columns if col not in categorical_features]

# Scale only numerical features
scaler = MinMaxScaler()
X_train_scaled = X_train.copy()
X_test_scaled = X_test.copy()

X_train_scaled[numerical_features] = scaler.fit_transform(X_train[numerical_features])
X_test_scaled[numerical_features] = scaler.transform(X_test[numerical_features])

# Ensure DataFrame maintains index integrity for Stratified K-Fold
X_train_scaled.reset_index(drop=True, inplace=True)
X_test_scaled.reset_index(drop=True, inplace=True)

# Convert y_train and y_test to Pandas Series before resetting index
y_train = pd.Series(y_train).reset_index(drop=True)
y_test = pd.Series(y_test).reset_index(drop=True)

# Save the scaler for inference
scaler_path = f"{local_data_dir}/scaler_XGBoost.pkl"
joblib.dump(scaler, scaler_path)
s3_client.upload_file(scaler_path, S3_BUCKET_NAME, f"{S3_FOLDER_NAME}/scaler_XGBoost.pkl")
print(f" Saved and uploaded scaler.")

# Convert scaled features back into DataFrame (after scaling they are NumPy arrays)
X_train_scaled = pd.DataFrame(X_train_scaled, columns=X_train.columns)
X_test_scaled = pd.DataFrame(X_test_scaled, columns=X_test.columns)

# Interaction Features
X_train_scaled["pitch_1_count_interaction"] = X_train_scaled["previous_pitch_1_encoded"] * X_train_scaled["count_encoded"]
X_train_scaled["pitcher_batter_matchup"] = X_train_scaled["pitcher_hand_encoded"] * X_train_scaled["batter_hand_encoded"]

X_test_scaled["pitch_1_count_interaction"] = X_test_scaled["previous_pitch_1_encoded"] * X_test_scaled["count_encoded"]
X_test_scaled["pitcher_batter_matchup"] = X_test_scaled["pitcher_hand_encoded"] * X_test_scaled["batter_hand_encoded"]


# Compute sample weights for class balancing
sample_weights = compute_sample_weight(class_weight="balanced", y=y_train)

# Use Stratified K-Fold Cross Validation**
kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# Define XGBoost hyperparameters
xgb_params = {
    "n_estimators": 900,  # Increase trees for more depth
    "learning_rate": 0.04,  # Lower learning rate for better generalization
    "max_depth": 9,  # Capture more feature interactions
    "subsample": 0.9,  # Reduce overfitting
    "colsample_bytree": 0.9,  # Feature sampling
    "gamma": 3,  # Pruning low-importance splits
    "min_child_weight": 4,  # Prevents overly complex trees
    "reg_lambda": 2,  # L2 Regularization
    "reg_alpha": 0.5,  # L1 Regularization
    "objective": "multi:softmax",
    "num_class": len(label_encoder.classes_),
    "random_state": 42,
    "use_label_encoder": False,
}

# Reset index for alignment with StratifiedKFold indices
X_train_scaled = pd.DataFrame(X_train_scaled, columns=X_train.columns)
X_test_scaled = pd.DataFrame(X_test_scaled, columns=X_test.columns)

y_train = pd.Series(y_train).reset_index(drop=True)
y_test = pd.Series(y_test).reset_index(drop=True)

# Ensure indices are sequential for compatibility with KFold
X_train_scaled.reset_index(drop=True, inplace=True)
X_test_scaled.reset_index(drop=True, inplace=True)

# Cross-validation loop
cv_accuracies = []
for fold, (train_idx, val_idx) in enumerate(kf.split(X_train_scaled, y_train), 1):
    print(f" Running Fold {fold}...")

    X_fold_train, X_fold_val = X_train_scaled.iloc[train_idx], X_train_scaled.iloc[val_idx]
    y_fold_train, y_fold_val = y_train.iloc[train_idx], y_train.iloc[val_idx]

    model = XGBClassifier(**xgb_params)

    # **Fix: Move `eval_metric` inside `evals` argument**
    model.fit(
        X_fold_train, y_fold_train,
        sample_weight=sample_weights[train_idx],
        eval_set=[(X_fold_val, y_fold_val)],
        verbose=False
    )

    # Predict and evaluate
    y_fold_pred = model.predict(X_fold_val)
    fold_acc = accuracy_score(y_fold_val, y_fold_pred)
    cv_accuracies.append(fold_acc)

    print(f" Fold {fold} Accuracy: {fold_acc:.4f}")

# Compute mean accuracy across folds
mean_cv_accuracy = np.mean(cv_accuracies)
print(f"\n Mean Cross-Validation Accuracy: {mean_cv_accuracy:.4f}")


# Compute new sample weights based on full dataset
final_sample_weights = compute_sample_weight(class_weight="balanced", y=y_train)

# Train final model on full dataset
final_model = XGBClassifier(**xgb_params)
final_model.fit(X_train_scaled, y_train, sample_weight=final_sample_weights)

# Evaluate on test data
y_test_pred = final_model.predict(X_test_scaled)
test_accuracy = accuracy_score(y_test, y_test_pred)

print(f"\n Final Test Accuracy: {test_accuracy:.4f}")
print("\n Classification Report:\n", classification_report(y_test, y_test_pred))

# Confusion Matrix**
conf_matrix = confusion_matrix(y_test, y_test_pred)
plt.figure(figsize=(10, 8))
sns.heatmap(conf_matrix, annot=True, fmt="d", cmap="Blues", xticklabels=label_encoder.classes_,
            yticklabels=label_encoder.classes_)
plt.xlabel("Predicted Pitch Type")
plt.ylabel("Actual Pitch Type")
plt.title("Confusion Matrix for XGBoost")
plt.show()

# Feature Importance**
feature_importance = final_model.feature_importances_
feature_importance_df = pd.DataFrame({"Feature": X_train.columns, "Importance": feature_importance}).sort_values(
    by="Importance", ascending=False)

print("\n🔝 Top Features:\n", feature_importance_df.head(15))

# **Plot Feature Importance**
plt.figure(figsize=(12, 6))
sns.barplot(x=feature_importance_df["Importance"][:15], y=feature_importance_df["Feature"][:15])
plt.xlabel("Feature Importance")
plt.ylabel("Feature Name")
plt.title("Top 15 Feature Importance for XGBoost")
plt.show()

perm_importance = permutation_importance(final_model, X_test_scaled, y_test, n_repeats=10, random_state=42)

perm_feature_importance_df = pd.DataFrame({
    "Feature": X_train.columns,
    "Importance": perm_importance.importances_mean
}).sort_values(by="Importance", ascending=False)

print("\n🔝 Permutation-Based Feature Importance:\n", perm_feature_importance_df.head(15))

# Save final model locally
model_path = f"{local_data_dir}/XGBoost_ModelB.pkl"
joblib.dump(final_model, model_path)

# Upload trained model to S3
s3_client.upload_file(model_path, S3_BUCKET_NAME, f"{S3_FOLDER_NAME}/XGBoost_ModelB.pkl")
print(f"\n XGBoost Model saved and uploaded to S3.")

print("\n Model Training & S3 Upload Complete! ")
