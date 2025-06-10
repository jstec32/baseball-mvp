#!/usr/bin/env python3
import os
import sys
import requests
import pandas as pd
import boto3
import psycopg2
from io import BytesIO
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

#
# ─────────────────────────────────────────────────────────────
#  1) CONFIGURATION: S3, Postgres, environment variables
# ─────────────────────────────────────────────────────────────
#

# S3 bucket/key for your game‐data CSV (used only to discover team_ids)
S3_BUCKET          = "baseball-data-mvp"
MLB_GAME_DATA_KEY  = "mlb_game_data/mlb_game_data_2025.csv"

# Postgres connection parameters (players table should already exist)
DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port":     int(os.getenv("DB_PORT", 5432)),
}

# MLB Stats API base URL
MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

# 30 MLB team IDs can be gleaned from your game CSV; we'll pull them dynamically.
# Example of one roster endpoint URL:
#   https://statsapi.mlb.com/api/v1/teams/{teamId}/roster?rosterType=active&season=2025


#
# ─────────────────────────────────────────────────────────────
#  2) HELPERS: load game‐data → extract team IDs
# ─────────────────────────────────────────────────────────────
#

def load_game_data_2025() -> pd.DataFrame:
    """
    Download 'mlb_game_data_2025.csv' from S3 and return as a pandas DataFrame.
    """
    s3 = boto3.client(
        "s3",
        aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name           = os.getenv("AWS_REGION", "us-east-1")
    )
    obj = s3.get_object(Bucket=S3_BUCKET, Key=MLB_GAME_DATA_KEY)
    df = pd.read_csv(BytesIO(obj["Body"].read()))
    return df

def get_all_team_ids_from_games(df_games: pd.DataFrame) -> list[int]:
    """
    Given the game‐data frame, return a sorted list of all distinct team IDs
    that appear either as home_team_id or away_team_id.
    """
    home_ids = df_games["home_team_id"].dropna().astype(int).unique()
    away_ids = df_games["away_team_id"].dropna().astype(int).unique()
    all_ids = set(home_ids.tolist() + away_ids.tolist())
    return sorted(all_ids)


#
# ─────────────────────────────────────────────────────────────
#  3) FETCH + PARSE each team’s 2025 ACTIVE roster
# ─────────────────────────────────────────────────────────────
#

def fetch_team_roster(team_id: int, season: int = 2025) -> dict:
    """
    Call MLB Stats API for a single team's active roster in the given season.
    Returns the raw JSON dictionary.
    """
    url = f"{MLB_API_BASE}/teams/{team_id}/roster"
    params = {
        "rosterType": "active",
        "season":     season
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def inspect_one_roster_json(raw_json: dict) -> None:
    """
    Print the top‐level keys and an example of the first player entry,
    so you can see exactly which fields are present.
    """
    print("Top‐level keys in JSON:", list(raw_json.keys()))
    if "roster" not in raw_json or not raw_json["roster"]:
        print("  No 'roster' key or it's empty.")
        return

    first = raw_json["roster"][0]
    print("Example roster‐entry keys:", list(first.keys()))
    if "person" in first:
        print(" → 'person' subkeys:", list(first["person"].keys()))
    if "position" in first:
        print(" → 'position' subkeys:", list(first["position"].keys()))
    if "batSide" in first:
        print(" → 'batSide' subkeys:", list(first["batSide"].keys()))
    if "pitchHand" in first:
        print(" → 'pitchHand' subkeys:", list(first["pitchHand"].keys()))
    if "team" in raw_json and isinstance(raw_json["teams"], list):
        # On many roster calls you'll also get a top‐level "teams":[ { ... } ] block
        print(" → 'teams' subkeys:", list(raw_json["teams"][0].keys()))


def parse_roster_to_df(raw_json: dict, team_id: int) -> pd.DataFrame:
    """
    Given the raw JSON from /teams/{teamId}/roster?rosterType=active&season=2025,
    return a DataFrame with exactly these columns:
      - mlbam_id     (INT)    → person.id
      - first_name   (TEXT)   → person.firstName (fallback: split from fullName)
      - last_name    (TEXT)   → person.lastName  (fallback: split from fullName)
      - full_name    (TEXT)   → person.fullName
      - team_id      (INT)    → the input param `team_id`
      - team_name    (TEXT)   → teams[0].name (if exists)
      - team_abbrev  (TEXT)   → teams[0].abbreviation (if exists)
      - position     (TEXT)   → entry["position"]["abbreviation"]
      - bats_hand    (TEXT)   → entry["batSide"]["code"]  ("L"/"R"/"S")
      - throws_hand  (TEXT)   → entry["pitchHand"]["code"] ("L"/"R")
    """
    out_records = []

    # The JSON often has a "teams" array describing that team’s metadata:
    team_name   = None
    team_abbrev = None
    if "teams" in raw_json and isinstance(raw_json["teams"], list) and raw_json["teams"]:
        team_obj = raw_json["teams"][0]
        team_name   = team_obj.get("name")
        team_abbrev = team_obj.get("abbreviation")

    for entry in raw_json.get("roster", []):
        person = entry.get("person", {})
        pos    = entry.get("position", {})

        # MLBAM ID
        mlbam_id    = person.get("id")            # e.g. 660271

        # Names
        full_name   = person.get("fullName")
        first_name  = person.get("firstName")
        last_name   = person.get("lastName")

        # If firstName/lastName are missing but fullName exists, split on first space
        if (not first_name or not last_name) and full_name:
            parts = full_name.strip().split(" ", 1)
            if len(parts) == 2:
                first_name, last_name = parts
            else:
                # Mononyms or unusual formats: store entire into first_name and leave last_name = None
                first_name = parts[0]
                last_name  = None

        # Position abbreviation, e.g. "SP", "CF", etc.
        position = pos.get("abbreviation")

        # Batting side
        bats_hand = None
        if "batSide" in entry and isinstance(entry["batSide"], dict):
            bats_hand = entry["batSide"].get("code")  # "L"/"R"/"S"

        # Throwing hand
        throws_hand = None
        if "pitchHand" in entry and isinstance(entry["pitchHand"], dict):
            throws_hand = entry["pitchHand"].get("code")  # "L"/"R"

        out_records.append({
            "mlbam_id":    mlbam_id,
            "first_name":  first_name,
            "last_name":   last_name,
            "full_name":   full_name,
            "team_id":     team_id,
            "team_name":   team_name,
            "team_abbrev": team_abbrev,
            "position":    position,
            "bats_hand":   bats_hand,
            "throws_hand": throws_hand
        })

    return pd.DataFrame(out_records)


#
# ─────────────────────────────────────────────────────────────
#  4) UPSET MISSING PLAYERS INTO Postgres “players” TABLE
# ─────────────────────────────────────────────────────────────
#
def upsert_missing_players(df_roster: pd.DataFrame) -> None:
    """
    Insert any players in df_roster whose mlbam_id is not already in players.key_mlbam.
    We assume `players.key_mlbam` has a UNIQUE constraint.
    The players table has columns:
      playerID, player_name, "First_Name", "Last_Name",
      team_full_name, teamID, "Position", "Bats", "Throws",
      key_mlbam, idfg
    """

    # 1) Determine which mlbam_id values already exist in players.key_mlbam
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()
    cur.execute("SELECT DISTINCT key_mlbam FROM players WHERE key_mlbam IS NOT NULL;")
    existing_ids = { row[0] for row in cur.fetchall() }
    cur.close()
    conn.close()

    # 2) Filter out those already present
    to_insert = df_roster[~df_roster["mlbam_id"].isin(existing_ids)].copy()
    if to_insert.empty:
        print("No new players to insert → all roster IDs are already in players table.")
        return

    # 3) Build a single INSERT … ON CONFLICT DO NOTHING
    insert_sql = """
        INSERT INTO players (
          "playerID",
          player_name,
          "First_Name",
          "Last_Name",
          team_full_name,
          "teamID",
          "Position",
          "Bats",
          "Throws",
          key_mlbam,
          idfg
        ) VALUES (
          %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT ("key_mlbam") DO NOTHING;
        """

    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()

    for _, row in to_insert.iterrows():
        full_name_nospaces = (row["full_name"] or "").replace(" ", "")
        player_id_value    = f"{full_name_nospaces}{row['mlbam_id']}"

        rec = (
            player_id_value,          # playerID = (full_name without spaces) + key_mlbam
            row["full_name"],         # player_name
            row["first_name"],        # First_Name
            row["last_name"],         # Last_Name
            row["team_name"],         # team_full_name
            row["team_abbrev"],       # teamID  (e.g. "NYY", "LAD", etc.)
            row["position"],          # Position
            row["bats_hand"],         # Bats
            row["throws_hand"],       # Throws
            row["mlbam_id"],          # key_mlbam
            None                      # idfg  (we leave it NULL for now)
        )
        cur.execute(insert_sql, rec)

    conn.commit()
    cur.close()
    conn.close()

    print(f"Inserted {len(to_insert)} new players into players table.")

if __name__ == "__main__":
    # 1) Load 2025 game data, extract team IDs
    print("→ Loading 2025 game data from S3...")
    df_games = load_game_data_2025()
    all_team_ids = get_all_team_ids_from_games(df_games)
    print(f"Found {len(all_team_ids)} distinct team IDs: {all_team_ids[:5]} …")

    if not all_team_ids:
        print("No team IDs found in game data – abort.")
        sys.exit(1)

    # 2) Fetch + parse each team’s roster
    print("→ Fetching rosters from MLB API …")
    all_dfs = []
    for tid in all_team_ids:
        try:
            raw_json = fetch_team_roster(tid, season=2025)

            df_this = parse_roster_to_df(raw_json, team_id=tid)
            all_dfs.append(df_this)
            print(f"   • Fetched {len(df_this)} players for team {tid}")
        except Exception as e:
            print(f"⚠️   Could not fetch roster for team {tid}: {e}")

    if all_dfs:
        df_all_rosters = pd.concat(all_dfs, ignore_index=True)
    else:
        df_all_rosters = pd.DataFrame(
            columns=[
                "mlbam_id","first_name","last_name","full_name",
                "team_id","team_name","team_abbrev","position",
                "bats_hand","throws_hand"
            ]
        )
    print(f"→ Total roster entries fetched: {len(df_all_rosters)}")


    print("→ Upserting any missing players into `players` table …")
    upsert_missing_players(df_all_rosters)


    out_csv = "all_mlb_rosters_2025.csv"
    df_all_rosters.to_csv(out_csv, index=False)
    print(f"→ Wrote combined roster CSV to {out_csv}")
