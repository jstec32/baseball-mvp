import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_curve, classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from joblib import load
import numpy as np

# Load the test dataset
test_data = pd.read_csv('/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/Test_2024.csv')

# 🚨 Define post-pitch features to remove (same as in training)
post_pitch_features = [
    'release_spin_rate', 'release_speed', 'pfx_x', 'pfx_z',
    'plate_x', 'plate_z'
]

# 🚨 Drop post-pitch features from X_test
X_test = test_data.drop(columns=['pitch_type_encoded'] + post_pitch_features, errors='ignore')
y_test = test_data['pitch_type_encoded']

# Load the trained model
model = load('/Users/joshsteckler/PycharmProjects/baseball-mvp/models/pitch_predictor_xgb.pkl')
print("Trained model loaded successfully.")

# 🚨 Verify that feature names match what the model expects
print(f"Features used in testing: {list(X_test.columns)}")
print(f"Features expected by model: {model.feature_names_in_}")

# Ensure all expected features exist in X_test
missing_features = set(model.feature_names_in_) - set(X_test.columns)
if missing_features:
    raise ValueError(f"Missing features in X_test: {missing_features}")

# Make predictions
y_pred = model.predict(X_test)

# 1️⃣ Classification Report
print("Classification Report:\n", classification_report(y_test, y_pred, zero_division=0))

# 2️⃣ Precision-Recall Curves
plt.figure(figsize=(8, 6))
for pitch_type in set(y_test):
    precision, recall, _ = precision_recall_curve(y_test == pitch_type, y_pred == pitch_type)
    plt.plot(recall, precision, label=f'Pitch Type {pitch_type}')

plt.xlabel("Recall")
plt.ylabel("Precision")
plt.title("Precision-Recall Curve for Each Pitch Type")
plt.legend()
plt.show()

# 3️⃣ Confusion Matrix
conf_matrix = confusion_matrix(y_test, y_pred)
plt.figure(figsize=(10, 8))
sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='Blues', xticklabels=model.classes_, yticklabels=model.classes_)
plt.xlabel("Predicted Pitch Type")
plt.ylabel("Actual Pitch Type")
plt.title("Confusion Matrix")
plt.show()

# Get feature importance values
feature_importance = model.feature_importances_

# Create a DataFrame to store feature importance
feature_importance_df = pd.DataFrame({
    'Feature': X_test.columns,
    'Importance': feature_importance
})

# Sort by importance (descending order)
feature_importance_df = feature_importance_df.sort_values(by='Importance', ascending=False)

# Display feature importance table
print(feature_importance_df)

# Optionally, save to CSV for later analysis
feature_importance_df.to_csv("feature_importance.csv", index=False)
print("Feature importance saved to feature_importance.csv")

# 📊 Visualizing Feature Importance
plt.figure(figsize=(10, 6))
sns.barplot(x=feature_importance_df['Importance'], y=feature_importance_df['Feature'])
plt.xlabel("Feature Importance")
plt.ylabel("Feature Name")
plt.title("Feature Importance in Random Forest Model")
plt.show()
