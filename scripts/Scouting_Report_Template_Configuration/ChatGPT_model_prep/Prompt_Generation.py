import argparse
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Hitter_Sequence_Chart import (
    fetch_statcast_data,
    generate_hitter_performance_chart,
    convert_to_structured_data_hitter,
)
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Hitter_Splits_Against_Arsenal_Data import \
    generate_hitter_splits_against_arsenal_data
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Pitch_Arsenal_Data import \
    generate_pitch_arsenal_data
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Pitcher_Heatmap_Data import \
    generate_pitcher_hitter_heatmap_data
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Pitcher_Sequence_Splits import (
    generate_pitcher_performance_chart,
    convert_to_structured_data_pitcher,
)
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Merge_data_pipeline import merge_scouting_and_historical_data
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.generate_pitcher_season_stats_data import \
    generate_pitcher_season_stats_data
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.hitter_season_stats_data import \
    generate_hitter_season_stats_data


def create_prompt_from_merged_data(combined_data):

    # Extract key data from the JSON
    batter_id = combined_data.get("batter_id", "UNKNOWN_BATTER")
    pitcher_id = combined_data.get("pitcher_id", "UNKNOWN_PITCHER")

    scouting_report = combined_data.get("scouting_report", {})
    historical_data = combined_data.get("historical_data", {})

    # Scouting report details
    hitter_season_stats = scouting_report.get("hitter_season_stats", {})
    pitcher_season_stats = scouting_report.get("pitcher_season_stats", {})
    hitter_splits = scouting_report.get("hitter_splits_against_arsenal", {})
    pitcher_arsenal = scouting_report.get("pitcher_arsenal", {})
    heatmap_data = scouting_report.get("heatmap_data", {})
    hitter_sequence_chart = scouting_report.get("hitter_sequence_chart", {})
    pitcher_sequence_splits = scouting_report.get("pitcher_sequence_splits", {})

    # Historical data details
    specific_matchup = historical_data.get("specific_matchup", {})

    league_wide = historical_data.get("league_wide_trends", [])
    similar_matchups = historical_data.get("similar_matchups", [])

    # Construct the prompt
    prompt = f"""
Context:
Batter ID: {batter_id}
- Hitter Season Stats: {hitter_season_stats.get('season_stats', {})}

Pitcher ID: {pitcher_id}
- Pitcher Season Stats: {pitcher_season_stats.get('season_stats', {})}

Scouting Report - Hitter Splits:
{hitter_splits}

Scouting Report - Pitcher Arsenal:
{pitcher_arsenal}

Scouting Report - Heatmap Data:
{heatmap_data}

Hitter Sequence Chart by Count:
{hitter_sequence_chart}

Pitcher Sequence Splits by Count:
{pitcher_sequence_splits}

Historical Specific Matchup:
- Full Data: {specific_matchup}

League-Wide Trends (Sample):
{league_wide[:3] if isinstance(league_wide, list) else []}

Similar Matchups:
{similar_matchups[:3] if isinstance(similar_matchups, list) else []}

Generate Recommendations:
1. Which pitch types & locations should the hitter focus on?
2. Based on similar historical matchups how should the hitter approach this at-bat?
3. When should the hitter be looking to swing, early in the count or late in the count based off of how the hitter & pitcher perform in counts?
4. What zone could the hitter do the most damage on?
    """.strip()

    return prompt

import json
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Merge_data_pipeline import (
    merge_scouting_and_historical_data,
)

if __name__ == "__main__":
    # Input dynamic batter and pitcher IDs
    batter_id = input("Enter Hitter ID: ")
    pitcher_id = input("Enter Pitcher ID: ")

    # Define the path to historical data
    historical_data_path = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/Historical_Data_3Layers"

    scouting_report_funcs = {
        "hitter_season_stats": lambda b, p: generate_hitter_season_stats_data(b),
        "pitcher_season_stats": lambda b, p: generate_pitcher_season_stats_data(p),
        "hitter_splits_against_arsenal": lambda b, p: generate_hitter_splits_against_arsenal_data(p, b),
        "pitcher_arsenal": lambda b, p: generate_pitch_arsenal_data(p),
        "heatmap_data": lambda b, p: generate_pitcher_hitter_heatmap_data(p, b),
        "hitter_sequence_chart": lambda b, p: convert_to_structured_data_hitter(
            generate_hitter_performance_chart(fetch_statcast_data(batter_id=b))
        ),
        "pitcher_sequence_splits": lambda b, p: convert_to_structured_data_pitcher(
            generate_pitcher_performance_chart(fetch_statcast_data(pitcher_id=p))
        ),
    }

    # Call the merge function directly (scouting_report_funcs is defined within it)
    combined_data = merge_scouting_and_historical_data(
        batter_id=batter_id,
        pitcher_id=pitcher_id,
        historical_data_path=historical_data_path,
        scouting_report_funcs=scouting_report_funcs,
    )

    # Generate the prompt using the combined data
    prompt = create_prompt_from_merged_data(combined_data)

    # Display the prompt
    print("\n=== Generated Prompt ===")
    print(prompt)