import os
from PIL import Image
import requests
from io import BytesIO
from pathlib import Path
from fpdf import FPDF
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import psycopg2
import seaborn as sns
from io import BytesIO
from fpdf.enums import XPos, YPos
from scripts.Database_Configuration.visualization_config import  apply_global_styles
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Hitter_Sequence_Chart import \
    convert_to_structured_data_hitter, generate_hitter_performance_chart, fetch_statcast_data
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Hitter_Splits_Against_Arsenal_Data import \
    generate_hitter_splits_against_arsenal_data
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Pitch_Arsenal_Data import \
    generate_pitch_arsenal_data
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Pitcher_Heatmap_Data import \
    generate_pitcher_hitter_heatmap_data
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Pitcher_Sequence_Splits import \
    generate_pitcher_performance_chart, convert_to_structured_data_pitcher
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.generate_pitcher_season_stats_data import \
    generate_pitcher_season_stats_data
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.hitter_season_stats_data import \
    generate_hitter_season_stats_data
from scripts.Scouting_Report_Template_Configuration.processing.rolling_avg_batter import fetch_rolling_averages_data, \
    compute_rolling_averages_from_db, plot_rolling_averages_for_pdf

# Import your individual Python scripts
from scripts.Scouting_Report_Template_Configuration.processing.Hitter_Season_Stats import generate_hitter_season_stats_visual
from scripts.Scouting_Report_Template_Configuration.processing.Hitter_Splits_Against_Pitcher_Arsenal import generate_hitter_splits_visual
from scripts.Scouting_Report_Template_Configuration.processing.Pitch_Arsenal_Visualization import generate_pitch_arsenal_visual
from scripts.Scouting_Report_Template_Configuration.processing.Pitcher_Heatmap import generate_pitcher_heatmap_visual
from scripts.Scouting_Report_Template_Configuration.processing.Season_Stats_Pitcher_Viz import generate_season_stats_viz
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Merge_data_pipeline import (
    merge_scouting_and_historical_data,
)
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Prompt_Generation import (
    create_prompt_from_merged_data,
)
from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Send_Prompt_Generation import (
    send_prompt_to_chatgpt,  # Import the existing function
)
plt.ioff()
# Database configuration
DB_CONFIG = {
    "host": "aws-0-us-east-2.pooler.supabase.com",
    "database": "postgres",
    "user": "postgres.chcovbrcpmlxyauansqe",
    "password": "1Z4IO6fxxYw8PgxL",  # Replace with your Supabase password
    "port": 5432
}

def figure_to_image(fig):

    buf = BytesIO()
    fig_width, fig_height = fig.get_size_inches()
    print(f"Figure dimensions (in inches): width={fig_width}, height={fig_height}")
    fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1, dpi=300)
    buf.seek(0)
    return buf

def fetch_player_name(player_id):
    query = """
    SELECT CONCAT("First_Name", ' ', "Last_Name") AS player_name
    FROM players
    WHERE key_mlbam = %s;
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query, (player_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error fetching player name: {e}")
        return None

def fetch_player_headshot(hitter_id):
    """
    Fetch the hitter's headshot image from MLB's database.
    """
    try:
        url = f'https://img.mlbstatic.com/mlb-photos/image/upload/w_213,d_people:generic:headshot:silo:current.png,q_auto:best,f_auto/v1/people/{hitter_id}/headshot/67/current'
        response = requests.get(url)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
        else:
            print(f"Failed to fetch headshot for hitter ID: {hitter_id} (status code: {response.status_code})")
            return None
    except Exception as e:
        print(f"Error fetching headshot for hitter ID {hitter_id}: {e}")
        return None

def generate_scouting_report(hitter_name, pitcher_name, visuals, pdf_path,recommendations):

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)  # Disable automatic page breaks
    pdf.add_page()

    # Layout settings
    page_width = 205  # Width of the page
    page_height = 277  # Height of the page (A4 page minus margins)
    margin = 10  # Margin around the page
    pdf.set_margins(margin, margin, margin)
    row_height = (page_height - (2 * margin)) / 4.5  # Divide into four rows
    content_width = page_width - (2 * margin)

    visual_width = (content_width / 2) - margin
    visual_height = row_height - 15
    scaled_visual_height = row_height * 0.7  # Reduce each visual height by 30%
    scaled_heatmap_height = row_height * 0.6  # Slightly smaller for the heatmap

    #generate headshot of hitter
    headshot = fetch_player_headshot(hitter_id)
    if headshot:
        headshot_buf = BytesIO()
        headshot.save(headshot_buf, format="PNG")
        headshot_buf.seek(0)
        # Add the headshot to the top-left corner
        pdf.image(headshot_buf, x=margin, y=margin , w=25, h=25)


    # Title at the top
    pdf.set_font("Helvetica", "B", 16)  # Larger, bold font for title
    pdf.set_text_color(0, 63, 92)  # Navy Blue
    pdf.set_xy(margin + 30, margin + 10)  # Adjust title position to align with headshot
    title_width = pdf.get_string_width(f"Scouting Report: {hitter_name} vs. {pitcher_name}")
    pdf.set_x((page_width - title_width) / 2)  # Center the title
    pdf.cell(0, 10, text=f"Scouting Report: {hitter_name} vs. {pitcher_name}", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)  # Add spacing below the title


    # --- Row 1: Pitcher Season Stats (Full Width) ---
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(0, 0, 0)  # Black text
    title_text = "Pitcher Season Stats"
    title_width = pdf.get_string_width(title_text)
    title_x = margin + (content_width / 2) - (title_width / 2)  # Center title relative to content width

    # Set the X position and render the title
    pdf.set_xy(title_x, pdf.get_y())
    pdf.cell(title_width, 10, text=title_text, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    y_pos = pdf.get_y()
    pdf.image(figure_to_image(visuals["Pitcher Season Stats"]), x=margin, y=y_pos, w=content_width, h=scaled_visual_height)
    pdf.ln(scaled_visual_height +5)  # Add space after visual

    # --- Row 2: Hitter Season Stats (Left) and Hitter Splits (Right) ---
    pdf.set_font("Helvetica", "B", 14)  # Match the font size and style of section titles
    pdf.set_text_color(0, 0, 0)  # Black text for the title

    title_text = f"{hitter_name} Advanced Breakdown"
    title_width = pdf.get_string_width(title_text)
    title_x = margin + (content_width / 2) - (title_width / 2)  # Center the title relative to the content width

    # Set position and render the title
    pdf.set_xy(title_x, pdf.get_y())
    pdf.cell(title_width, 10, text=title_text, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    y_pos_left = pdf.get_y()
    y_pos_right = y_pos_left

    # Fix consistent table heights
    table_height = scaled_visual_height

    rolling_avg_fig = visuals["Rolling Averages"]  # Assuming this key contains the rolling averages figure
    pdf.image(
        figure_to_image(rolling_avg_fig),
        x=margin,
        y=y_pos_left,
        w=(content_width / 2) - margin,
        h=table_height
    )

    pdf.image(figure_to_image(visuals["Hitter Splits Against Arsenal"]), x=(page_width / 2) + margin / 2, y=y_pos_right, w=(content_width / 2) - margin, h=table_height)
    pdf.ln(scaled_visual_height + 5)

    # --- Row 3: Combined Heatmap ---
    remaining_height = page_height - pdf.get_y() - margin
    pdf.set_font("Helvetica", "B", 14)

    # Center the title for Combined Heatmap
    heatmap_title = f"{hitter_name} vs. {pitcher_name} Heatmap"
    title_width = pdf.get_string_width(heatmap_title)
    heatmap_title_x = margin + (content_width / 2) - (title_width / 2)  # Center title over the heatmap
    pdf.set_xy(heatmap_title_x, pdf.get_y())
    pdf.cell(title_width, 10, heatmap_title, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Adjust heatmap position and dimensions
    heatmap_y = pdf.get_y()
    scaled_heatmap_height = row_height * 0.8
    pdf.image(figure_to_image(visuals["Pitcher Heatmap"]), x=margin, y=heatmap_y, w=content_width,
              h=min(scaled_heatmap_height, remaining_height - 5))
    pdf.ln(scaled_heatmap_height + 5)

    # --- Row 4: Pitch Usage Rate and Recommendations ---
    pdf.set_font("Helvetica", "B", 14)

    # Dynamically center "Pitch Usage Rate" title
    pitch_usage_title = "Pitch Usage Rate"
    title_width = pdf.get_string_width(pitch_usage_title)
    pitch_usage_x = margin + (content_width / 4) - (title_width / 2)  # Center within left half
    pdf.set_xy(pitch_usage_x, pdf.get_y())
    pdf.cell(title_width, 10, pitch_usage_title, align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)

    # Dynamically center "Recommendations" title
    recommendations_title = "Recommendations"
    title_width = pdf.get_string_width(recommendations_title)
    recommendations_x = margin + (3 * content_width / 4) - (title_width / 2)  # Center within right half
    pdf.set_xy(recommendations_x, pdf.get_y())
    pdf.cell(title_width, 10, recommendations_title, align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Add visualizations and text
    y_pos = pdf.get_y()
    pdf.image(figure_to_image(visuals["Pitcher Arsenal"]), x=margin, y=y_pos, w=(content_width / 2) - margin,
              h=scaled_visual_height)
    pdf.set_xy((page_width / 2) + margin / 2, y_pos)
    pdf.set_font("Helvetica", size=8)
    pdf.multi_cell((content_width / 2) - margin, 4, text=recommendations, border=1, align='L')
    pdf.ln(scaled_visual_height + 5)

    pdf.output(pdf_path)
    print(f"Scouting report saved to: {pdf_path}")


def run_pdf_generation(hitter_id, pitcher_id):
    print("Generating scouting report...")

    hitter_name = fetch_player_name(hitter_id)
    pitcher_name = fetch_player_name(pitcher_id)

    if not hitter_name or not pitcher_name:
        print(f"Failed to fetch names for Hitter ID: {hitter_id} or Pitcher ID: {pitcher_id}")
        return

    print(f"Hitter: {hitter_name}, Pitcher: {pitcher_name}")

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

    historical_data_path = "/Users/joshsteckler/PycharmProjects/baseball-mvp/docs/StatCast CSV Data/Historical_Data_3Layers"
    combined_data = merge_scouting_and_historical_data(hitter_id, pitcher_id, scouting_report_funcs,historical_data_path)
    prompt = create_prompt_from_merged_data(combined_data)

    recommendations = send_prompt_to_chatgpt(prompt)
    recommendations = recommendations.replace("’", "'").replace("“", '"').replace("”", '"')
    print("\n=== ChatGPT Recommendations ===")
    print(recommendations)

    rolling_avg_data = compute_rolling_averages_from_db(hitter_id)  # Ensure this function exists
    if rolling_avg_data is None or rolling_avg_data.empty:
        print(f"No rolling average data available for hitter ID: {hitter_id}")
        return
    rolling_avg_fig = plot_rolling_averages_for_pdf(hitter_id, rolling_avg_data, return_fig=True)

    # Generate visuals
    rolling_avg_fig = plot_rolling_averages_for_pdf(hitter_id, rolling_avg_data, return_fig=True)
    hitter_splits_visuals = generate_hitter_splits_visual(pitcher_id, hitter_id)
    pitcher_arsenal_visuals = generate_pitch_arsenal_visual(pitcher_id)
    pitcher_heatmap_visuals = generate_pitcher_heatmap_visual(pitcher_id, hitter_id)
    pitcher_season_stats_visual = generate_season_stats_viz(pitcher_id)

    if not all([rolling_avg_fig, hitter_splits_visuals, pitcher_arsenal_visuals, pitcher_heatmap_visuals]):
        print("Failed to generate one or more visuals.")
        return

    visuals = {
        "Rolling Averages": rolling_avg_fig,
        "Pitcher Season Stats": pitcher_season_stats_visual,
        "Hitter Splits Against Arsenal": hitter_splits_visuals["hitter_splits_table"],
        "Pitcher Arsenal": pitcher_arsenal_visuals["usage_rate"],
        "Pitcher Heatmap": pitcher_heatmap_visuals,  # Dictionary of heatmaps per pitch type
    }

    pdf_path = "/Users/joshsteckler/PycharmProjects/baseball-mvp/scouting_reports/scouting_report"+hitter_name+".pdf"
    generate_scouting_report(hitter_name, pitcher_name, visuals, pdf_path,recommendations)
    print("Scouting report generation complete.")

if __name__ == "__main__":
    hitter_id = input("Enter Hitter ID: ")
    pitcher_id = input("Enter Pitcher ID: ")
    run_pdf_generation(hitter_id, pitcher_id)