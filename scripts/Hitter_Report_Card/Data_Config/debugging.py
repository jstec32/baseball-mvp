import pandas as pd
import requests
from io import StringIO

# Statcast CSV URL (adjust dates or filters as needed)
url = "https://baseballsavant.mlb.com/statcast_search/csv?all=true&type=details&player_type=pitcher&game_date_gt=2025-04-23&game_date_lt=2025-04-23"

# Add browser headers to trick the server
headers = {
    "User-Agent": "Mozilla/5.0"
}

# Download the CSV with browser-like headers
response = requests.get(url, headers=headers)

# Check for issues
if response.status_code == 200:
    df = pd.read_csv(StringIO(response.text))
    print("✅ Successfully loaded:", df.shape)
    print(df.head())
else:
    print(f"❌ Failed with status code {response.status_code}")

