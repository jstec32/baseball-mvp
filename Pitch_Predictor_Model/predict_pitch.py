import pandas as pd
import numpy as np
from joblib import load

# Load the trained model and encoder
model = load('/Users/joshsteckler/PycharmProjects/baseball-mvp/models/pitch_predictor_rf.pkl')
encoder = load('/Users/joshsteckler/PycharmProjects/baseball-mvp/models/pitch_type_encoder.pkl')


# Load required feature names from the model
required_features = model.feature_names_in_

def predict_next_pitch(game_context):
    # Convert game context into a DataFrame
    input_df = pd.DataFrame([game_context])

    # Dynamically handle one-hot encoding for the count column
    count_value = input_df['count'].iloc[0]  # Example: "1-2"
    count_one_hot = pd.DataFrame(0, index=[0], columns=[f'count_{count_value}'])

    # Merge one-hot-encoded count into the input DataFrame
    input_df = pd.concat([input_df.drop(columns=['count']), count_one_hot], axis=1)

    # Ensure all expected features are present
    for feature in required_features:
        if feature not in input_df.columns:
            input_df[feature] = 0  # Fill missing features with 0

    # Reorder columns to match model’s training order
    input_df = input_df[required_features]

    # Predict probabilities for each pitch type
    probabilities = model.predict_proba(input_df)[0]

    # Get the most likely pitch type
    most_likely_pitch_index = np.argmax(probabilities)
    most_likely_pitch = encoder.inverse_transform([most_likely_pitch_index])[0]

    # Prepare prediction results
    prediction_results = {
        "predicted_pitch_type": most_likely_pitch,
        "pitch_probabilities": {
            encoder.inverse_transform([i])[0]: round(prob, 2) for i, prob in enumerate(probabilities)
        }
    }
    return prediction_results

# Example game context
game_context = {
    "pitcher_id": 12345,
    "batter_id": 67890,
    "count": "0-2",  # Dynamically handled for one-hot encoding
    "on_1b": 0,
    "on_2b": 0,
    "on_3b": 0,
    "release_speed": 92.5,
    "release_spin_rate": 2200,
    "plate_x": -0.5,
    "plate_z": 2.0,
    "pfx_x": -1.5,
    "pfx_z": 4.0,
    "runners_on": 1,
    "stand_L": 1,
    "p_throws_L": 0,
    "inning": 3,
    "inning_topbot_BOT": 1,
    "outs_when_up": 1,
}

result = predict_next_pitch(game_context)
print("Predicted Next Pitch Type:", result["predicted_pitch_type"])
print("Pitch Probabilities:", result["pitch_probabilities"])
