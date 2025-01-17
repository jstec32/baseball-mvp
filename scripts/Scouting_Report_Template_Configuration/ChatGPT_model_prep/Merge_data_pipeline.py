import pandas as pd
import json
import os
from decimal import Decimal
from json import JSONEncoder


from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.generate_pitcher_season_stats_data import generate_pitcher_season_stats_data
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.hitter_season_stats_data import generate_hitter_season_stats_data
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Hitter_Splits_Against_Arsenal_Data import generate_hitter_splits_against_arsenal_data
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Pitch_Arsenal_Data import generate_pitch_arsenal_data
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Pitcher_Heatmap_Data import generate_pitcher_hitter_heatmap_data

class DecimalEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def merge_scouting_and_historical_data(
    batter_id,
    pitcher_id,
    scouting_report_funcs,
    historical_data_path,
    output_path
):
    """
    Merge scouting report data + historical data into one structure for a
    given batter_id and pitcher_id. Returns the combined structure and writes
    it to a JSON file for reference.
    """
    # Initialize combined data
    combined_data = {
        "batter_id": batter_id,
        "pitcher_id": pitcher_id,
        "scouting_report": {},
        "historical_data": {}
    }

    # STEP 1: Fetch scouting report data in memory
    for key, func in scouting_report_funcs.items():
        try:
            combined_data["scouting_report"][key] = func(batter_id, pitcher_id)
        except Exception as e:
            print(f"Error generating {key}: {e}")
            combined_data["scouting_report"][key] = None

    # STEP 2: Fetch historical data
    try:
        # 2a. Specific matchup
        specific_matchup_file = os.path.join(historical_data_path, "specific_matchup_data.csv")
        specific_df = pd.read_csv(specific_matchup_file)
        sm_match = specific_df[
            (specific_df["batter_id"] == batter_id) &
            (specific_df["pitcher_id"] == pitcher_id)
        ].to_dict(orient="records")
        combined_data["historical_data"]["specific_matchup"] = sm_match[0] if sm_match else None

        # 2b. League-wide trends
        league_wide_file = os.path.join(historical_data_path, "league_wide_trends.csv")
        league_wide_df = pd.read_csv(league_wide_file)
        combined_data["historical_data"]["league_wide_trends"] = league_wide_df.to_dict(orient="records")

        # 2c. Similar matchups
        similar_file = os.path.join(historical_data_path, "similar_matchup_data.csv")
        similar_df = pd.read_csv(similar_file)
        combined_data["historical_data"]["similar_matchups"] = similar_df.to_dict(orient="records")

    except Exception as e:
        print(f"Error loading historical data: {e}")
        combined_data["historical_data"] = None

    # STEP 3: Write combined_data to a JSON file
    output_file = os.path.join(output_path, f"combined_data_{batter_id}_{pitcher_id}.json")
    with open(output_file, "w") as f:
        # Use custom encoder so Decimal objects don't break json.dump
        json.dump(combined_data, f, indent=4, cls=DecimalEncoder)
    print(f"Combined data saved to: {output_file}")

    # STEP 4: Return combined_data in memory (for direct usage in prompt generation)
    return combined_data


# Corrected version of `scouting_report_funcs` using lambdas:
scouting_report_funcs = {
    "hitter_season_stats": lambda b, p: generate_hitter_season_stats_data(b),
    "pitcher_season_stats": lambda b, p: generate_pitcher_season_stats_data(p),
    "hitter_splits_against_arsenal": lambda b, p: generate_hitter_splits_against_arsenal_data(p, b),
    "pitcher_arsenal": lambda b, p: generate_pitch_arsenal_data(p),
    "heatmap_data": lambda b, p: generate_pitcher_hitter_heatmap_data(p, b)
}

if __name__ == "__main__":
    # Example IDs (strings if your DB columns are TEXT)
    batter_id = "518692"
    pitcher_id = "605400"

    historical_data_path = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/Historical_Data_3Layers"
    output_path = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/Combined_Data"

    combined_data = merge_scouting_and_historical_data(
        batter_id,
        pitcher_id,
        scouting_report_funcs,
        historical_data_path,
        output_path
    )


