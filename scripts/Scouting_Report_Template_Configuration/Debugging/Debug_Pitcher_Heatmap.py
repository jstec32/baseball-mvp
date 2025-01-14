from scripts.Scouting_Report_Template_Configuration.processing.Pitcher_Heatmap import generate_pitcher_heatmap_visual

def test_generate_pitcher_heatmap_visual(pitcher_id, hitter_id):
    try:
        # Call the function
        heatmaps = generate_pitcher_heatmap_visual(pitcher_id, hitter_id)

        if not heatmaps:
            print("No heatmaps generated. The function returned an empty dictionary.")
            return

        # Verify that all pitch types are included
        expected_pitch_types = ["Fastball", "Slider", "Curveball", "Changeup"]  # Adjust as needed
        missing_pitch_types = [pitch for pitch in expected_pitch_types if pitch not in heatmaps]

        if missing_pitch_types:
            print(f"Missing heatmaps for pitch types: {missing_pitch_types}")
        else:
            print("All expected heatmaps are generated.")

        # Display the generated heatmaps
        for pitch_type, heatmap_fig in heatmaps.items():
            print(f"Displaying heatmap for {pitch_type}...")
            heatmap_fig.show()  # Show each heatmap for manual verification

    except Exception as e:
        print(f"Error testing generate_pitcher_heatmap_visual: {e}")

if __name__ == "__main__":
    # Replace with valid pitcher_id and hitter_id
    pitcher_id = input("Enter Pitcher ID: ")
    hitter_id = input("Enter Hitter ID: ")
    test_generate_pitcher_heatmap_visual(pitcher_id, hitter_id)
