import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_recall_curve, classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from joblib import load

# Load the test dataset
test_data = pd.read_csv('/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/Test_2024.csv')

# Separate features (X) and target (y)
X_test = test_data.drop(columns=['pitch_type_encoded'])
y_test = test_data['pitch_type_encoded']

# Load the trained model
model = load('/Users/joshsteckler/PycharmProjects/baseball-mvp/models/pitch_predictor_rf.pkl')
print("Trained model loaded successfully.")

# Make predictions
y_pred = model.predict(X_test)

# 1️⃣ Classification Report
print("Classification Report:\n", classification_report(y_test, y_pred))

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
