import pandas as pd
from pybaseball import schedule_and_record
import psycopg2
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)


mlb_teams = [
    "ARI", "ATL", "BAL", "BOS", "CHC", "CHW", "CIN", "CLE", "COL",
    "DET", "HOU", "KCR", "LAA", "LAD", "MIA", "MIL", "MIN", "NYM",
    "NYY", "OAK", "PHI", "PIT", "SDP", "SFG", "SEA", "STL", "TBR",
    "TEX", "TOR", "WSN"
]


def gather_games_data(teams, start_year=2020, end_year=2020):
    """
    Loop through each year/team, gather schedule, and return a combined DataFrame.
    """
    all_games = []

    for year in range(start_year, end_year + 1):
        for team in teams:
            try:
                # Pull schedule for the given team and year
                schedule_df = schedule_and_record(year, team)

                # Add context columns
                schedule_df["Year"] = year
                schedule_df["Team"] = team

                # Append to the list
                all_games.append(schedule_df)
            except Exception as e:
                print(f"Failed to retrieve schedule for {team}, {year}: {e}")

    # Combine all DataFrames into one
    if all_games:
        combined_df = pd.concat(all_games, ignore_index=True)
    else:
        combined_df = pd.DataFrame()

    return combined_df


def transform_games_data(df):
    """
    Transform the raw pybaseball schedule DataFrame into a format
    suitable for insertion into your `games` table.
    """


    # Rename 'Date' -> 'raw_date' so we don't collide with the actual datetime conversion
    df.rename(columns={"Date": "raw_date"}, inplace=True)

    #Create a proper 'game_date' by combining 'raw_date' + 'Year'
    df["game_date"] = pd.to_datetime(
        df["raw_date"] + " " + df["Year"].astype(str),
        # The format is somewhat loose, so we let pandas try to infer
        errors="coerce"
    )

    #Determine home/away teams
    df["home_team"] = df.apply(
        lambda x: x["Tm"] if x["Home_Away"] != "@" else x["Opp"],
        axis=1
    )
    df["away_team"] = df.apply(
        lambda x: x["Opp"] if x["Home_Away"] != "@" else x["Tm"],
        axis=1
    )

    #Build final_score as "R-RA" (if both columns are not null)
    def score_str(r_val, ra_val):
        if pd.notnull(r_val) and pd.notnull(ra_val):
            return f"{int(r_val)}-{int(ra_val)}"
        return None

    df["final_score"] = df.apply(
        lambda x: score_str(x["R"], x["RA"]),
        axis=1
    )

    #
    def get_winner(row):
        if row["W/L"] == "W":
            return row["Tm"]
        elif row["W/L"] == "L":
            return row["Opp"]
        return None

    df["winning_team"] = df.apply(get_winner, axis=1)

    #Construct a simplistic 'game_id'

    df["game_id"] = df.apply(
        lambda x: f"{x['Year']}_{x['Tm']}_{x.name}",  # Example: '2020_ARI_37'
        axis=1
    )

    df["game_date"] = pd.to_datetime(df["raw_date"] + " " + df["Year"].astype(str), errors="coerce").dt.date

    # Option A: Drop rows where game_date is NaT
    df = df.dropna(subset=["game_date"])



    # Select final columns you want to keep in your `games` table
    final_df = df[[
        "game_id",
        "game_date",
        "home_team",
        "away_team",
        "winning_team",
        "final_score",
        "Year",
        "Tm",  # optional if you need it
        "Opp",  # optional
        "W/L",  # optional
        "raw_date"  # optional to see the original date text
    ]].copy()

    return final_df

