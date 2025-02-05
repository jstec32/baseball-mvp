import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt

# Load the datasets
train_data = pd.read_csv('/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/Train_2024.csv')
test_data = pd.read_csv('/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/Test_2024.csv')

# Ensure count_* columns are properly cast as int64
for col in train_data.columns:
    if col.startswith('count_'):
        train_data[col] = train_data[col].astype('int64')

for col in test_data.columns:
    if col.startswith('count_'):
        test_data[col] = test_data[col].astype('int64')

# Separate features (X) and target (y)
X_train = train_data.drop(columns=['pitch_type_encoded'])
y_train = train_data['pitch_type_encoded']

X_test = test_data.drop(columns=['pitch_type_encoded'])
y_test = test_data['pitch_type_encoded']


# Initialize the Random Forest model with balanced class weights
model = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42)

# Train the model
model.fit(X_train, y_train)

joblib.dump(model, '/Users/joshsteckler/PycharmProjects/baseball-mvp/models/pitch_predictor_rf.pkl')
print("Trained model saved successfully.")

# Make predictions
y_pred = model.predict(X_test)

# Accuracy
accuracy = accuracy_score(y_test, y_pred)
print(f"Accuracy: {accuracy:.2f}")

# Classification Report
print("Classification Report:\n", classification_report(y_test,y_pred))


# Confusion Matrix
conf_matrix = confusion_matrix(y_test, y_pred)

# Plot the confusion matrix
plt.figure(figsize=(10, 8))
sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='Blues', xticklabels=model.classes_, yticklabels=model.classes_)
plt.xlabel("Predicted Pitch Type")
plt.ylabel("Actual Pitch Type")
plt.title("Confusion Matrix")
plt.show()

