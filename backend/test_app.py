import requests
import json

# API endpoint
url = "http://127.0.0.1:5000/predict"

# Game context data to send to the API
game_context = {
    "pitcher_id": 605400,
    "batter_id": 518692,
    "count": "1-2",
    "on_1b": 1,
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
    "outs_when_up": 1
}

print("DEBUG: Game context being sent:")
for key, value in game_context.items():
    print(f"{key}: {value} ({type(value)})")

# Send POST request to the API
response = requests.post(url, json=game_context)

# Check the response
if response.status_code == 200:
    print("API Response:")
    print(json.dumps(response.json(), indent=4))
else:
    print(f"API request failed with status code {response.status_code}")
    print(response.text)
    print("Sending request with game context:", json.dumps(game_context, indent=4))

