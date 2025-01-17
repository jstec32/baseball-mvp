
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Merge_data_pipeline import merge_scouting_and_historical_data


def create_prompt_from_merged_data(combined_data):
    """
    Create a structured prompt from the combined scouting report + historical data.

    Args:
        combined_data (dict): The dictionary returned by merge_scouting_and_historical_data,
                              containing 'scouting_report' and 'historical_data' sections.

    Returns:
        str: A string prompt ready to be passed to GPT-4 (or another LLM).
    """

    # Basic info
    batter_id = combined_data.get("batter_id", "UNKNOWN_BATTER")
    pitcher_id = combined_data.get("pitcher_id", "UNKNOWN_PITCHER")

    # Scouting report sections (may be None if they returned no data)
    scouting_report = combined_data.get("scouting_report", {})
    hitter_season_stats = scouting_report.get("hitter_season_stats", {})
    pitcher_season_stats = scouting_report.get("pitcher_season_stats", {})
    hitter_splits = scouting_report.get("hitter_splits_against_arsenal", {})
    pitcher_arsenal = scouting_report.get("pitcher_arsenal", {})
    heatmap_data = scouting_report.get("heatmap_data", {})

    # Historical data sections
    historical_data = combined_data.get("historical_data", {})
    specific_matchup = historical_data.get("specific_matchup", {})
    league_wide = historical_data.get("league_wide_trends", [])
    similar_matchups = historical_data.get("similar_matchups", [])

    # Extract some example fields (adjust to your actual data structure)
    # 1) Hitter stats
    hitter_season_detail = hitter_season_stats.get("season_stats", {}) if isinstance(hitter_season_stats, dict) else {}
    # 2) Pitcher stats
    pitcher_season_detail = pitcher_season_stats.get("season_stats", {}) if isinstance(pitcher_season_stats,
                                                                                       dict) else {}
    # 3) Most common pitch from specific matchup
    matchup_pitch = specific_matchup.get("most_common_pitch", "UNKNOWN")
    # 4) Example from league-wide trends
    league_snippet = league_wide[:3] if isinstance(league_wide, list) else []

    # Construct the prompt
    prompt = f"""
Context:
Batter ID: {batter_id}
- Hitter Season Stats: {hitter_season_detail}

Pitcher ID: {pitcher_id}
- Pitcher Season Stats: {pitcher_season_detail}

Scouting Report - Hitter Splits:
{hitter_splits}

Scouting Report - Pitcher Arsenal:
{pitcher_arsenal}

Scouting Report - Heatmap Data:
{heatmap_data}

Historical Specific Matchup:
- Most Common Pitch: {matchup_pitch}
- Full Data: {specific_matchup}

League-Wide Trends (Sample):
{league_snippet}

Similar Matchups:
(Example of similar matchups or archetypes) 
{similar_matchups[:3]}

Generate Recommendations:
1. Which pitch types & locations should the hitter focus on?
2. How should the pitcher approach high-leverage counts?
3. Are there defensive positioning suggestions based on this data?
4. Any strategic insights from similar matchups?
    """.strip()

    return prompt


if __name__ == "__main__":
    from decimal import Decimal

    # Suppose you already called merge_scouting_and_historical_data earlier
    # This is a mock combined_data for demonstration:
    combined_data_mock = {
        "batter_id": "518692",
        "pitcher_id": "605400",
        "scouting_report": {
            "hitter_season_stats": {
                "season_stats": {"ba": 0.321, "ops": 0.900}
            },
            "pitcher_season_stats": {
                "season_stats": {"era": 3.15, "whip": 1.05}
            },
            "hitter_splits_against_arsenal": {"splits": "..."},
            "pitcher_arsenal": {"most_common_pitch": "SL", "avg_velocity": 85.6},
            "heatmap_data": {"zone_distribution": {"1.0": 0.2, "2.0": 0.3}}
        },
        "historical_data": {
            "specific_matchup": {
                "most_common_pitch": "SL",
                "top_zone": "2.0",
                "some_stats": "..."
            },
            "league_wide_trends": [
                {"pitch_type": "SL", "zone": 2.0, "usage_percent": 20.0},
                {"pitch_type": "FF", "zone": 1.0, "usage_percent": 15.0}
            ],
            "similar_matchups": [
                {"hitter_archetype": "Power Hitter", "pitcher_archetype": "High Spin", "zone_distribution": "..."},
                {"hitter_archetype": "Contact Hitter", "pitcher_archetype": "Average Spin", "zone_distribution": "..."},
            ]
        }
    }

    # Create the prompt
    prompt = create_prompt_from_merged_data(combined_data_mock)

    print("\n=== Prompt ===")
    print(prompt)


