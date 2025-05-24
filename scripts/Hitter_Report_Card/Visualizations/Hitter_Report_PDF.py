import os
import unicodedata
import webbrowser

import boto3
import json

import pandas as pd
import psycopg2
import rembg
from fpdf import FPDF
from pdf2image import convert_from_path
import requests
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

from scripts.Hitter_Report_Card.Visualizations.Critical_Moments_Table import fetch_critical_moments, \
    visualize_critical_moments_table, TEAM_COLORS, generate_critical_moments_visual
from scripts.Hitter_Report_Card.Visualizations.Hitter_Game_Performance import visualize_hitter_game_performance_table, \
    load_box_scores_from_s3, generate_hitter_game_performance_visual
from scripts.Hitter_Report_Card.Visualizations.Hitter_Heatmap_Viz import generate_hitter_heatmap
from scripts.Hitter_Report_Card.Visualizations.Hitter_Season_Stats_RC import fetch_hitter_stats_and_team, \
    visualize_recent_hitter_stats_table
from scripts.Hitter_Report_Card.Visualizations.Spraychart_viz import generate_spray_chart_visual
from scripts.Hitter_Report_Card.Visualizations.rolling_stats_batter import generate_and_plot_rolling_averages

# Load environment variables
load_dotenv()

# Database Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT", 5432)
}

# S3 Configuration
S3_BUCKET = "scouting-reports-bucket"
S3_KEY = "All Real Teams and Logos v2.json"
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = "baseball-data-mvp"
MERGED_KEY = "mlb_game_data/merged_pitch_box_scores_2025.csv"

def remove_accents(input_str):
    return ''.join(
        c for c in unicodedata.normalize('NFD', input_str)
        if unicodedata.category(c) != 'Mn'
    )
# Fetch player name from the database
def fetch_player_name(player_id):
    query = """SELECT CONCAT("First_Name", ' ', "Last_Name") AS player_name, "Position","Bats"  FROM players WHERE key_mlbam = %s;"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query, (player_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            return result[0], result[1],result[2]  # (player_name, position)
        else:
            return None, None, None  # Handle missing data gracefully

    except Exception as e:
        print(f"Error fetching player name: {e}")
        return None

# Fetch game ID from pitch_data based on player_id and date
def fetch_game_id(player_id, game_date):
    query = """SELECT DISTINCT game_id FROM pitch_data WHERE batter_id = %s AND game_date = %s limit 1;"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query, (player_id, game_date))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error fetching game_id: {e}")
        return None

# Load team logos from S3 JSON file
def load_team_logos_from_s3():

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
        teams_data = json.loads(response['Body'].read().decode('utf-8'))

        # Print sample data to verify structure
        print("Successfully loaded team logos from S3")

        # Extract logos correctly
        return {f"{team['region']} {team['name']}": team['imgURL'] for team in teams_data['teams']}
    except Exception as e:
        print(f"Failed to load team logos from S3: {e}")
        return {}  # Return empty dictionary to avoid crashes

#Fetch Player's Opponent
def load_player_opponent(game_id,team_name):
    S3_BUCKET = "baseball-data-mvp"
    S3_FOLDER = "mlb_game_data"
    S3_KEY = "mlb_game_data_2025.csv"
    S3_full_key = f"{S3_FOLDER}/{S3_KEY}"
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=S3_full_key)
        df_games = pd.read_csv(StringIO(response["Body"].read().decode("utf-8")))
        # Ensure game_id column is in the right format
        df_games["game_id"] = df_games["game_id"].astype(str)
        game_id = str(game_id)  # Convert game_id to string for matching

        # Find the matching game
        game_row = df_games[df_games["game_id"] == game_id]
        if game_row.empty:
            print(f"No game found for game_id {game_id}.")
            return "Opponent Unknown"

        # Get home and away teams
        row = game_row.iloc[0]  # Select the first match (there should only be one)
        home_team = row["home_team"]
        away_team = row["away_team"]

        # Check which team is NOT the player's team (that is the opponent)
        opponent = away_team if home_team == team_name else home_team if away_team == team_name else None

        if opponent:
            return opponent
        else:
            print(f"Team {team_name} not found in game_id {game_id}. Possible data issue.")
            return "Opponent Unknown"

    except Exception as e:
        print(f"Error fetching opponent from S3: {e}")
        return "Opponent Unknown"


# Fetch team logo from URL
def fetch_team_logo(team_name):
    """Fetch the team logo from S3."""
    S3_BUCKET = "scouting-reports-bucket"
    S3_LOGO_FOLDER = "team_logos"
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    # Format the team name for the correct S3 key
    s3_key = f"{S3_LOGO_FOLDER}/{team_name.replace(' ', '_')}.png"
    print(s3_key)
    try:
        # Attempt to fetch the logo from S3
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        logo_img = Image.open(BytesIO(response['Body'].read()))
        print(f"Successfully fetched logo for {team_name}.")
        return logo_img

    except s3_client.exceptions.NoSuchKey:
        print(f"Warning: No logo found for team {team_name}. Using default logo.")
        return None  # Return None if logo doesn't exist

    except Exception as e:
        print(f"Error fetching logo for {team_name}: {e}")
        return None  # Return None if any error occurs

# Fetch player headshot
def fetch_player_headshot(player_id):
    """Fetches the player's headshot and removes the background if possible."""
    url = f'https://img.mlbstatic.com/mlb-photos/image/upload/w_213,d_people:generic:headshot:silo:current.png,q_auto:best,f_auto/v1/people/{player_id}/headshot/67/current'
    response = requests.get(url)

    if response.status_code == 200:
        img = Image.open(BytesIO(response.content)).convert("RGBA")

        try:
            # Remove background using rembg
            img_no_bg = rembg.remove(img)
            return img_no_bg
        except Exception as e:
            print(f"Background removal failed: {e}. Using default image.")

        return img
    else:
        print("Failed to fetch player headshot.")
        return None

def get_game_score_from_s3(game_id, batter_id):
    """Loads merged game data from S3 and returns scaled game score for one hitter/game."""
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )

        response = s3.get_object(Bucket=AWS_BUCKET_NAME, Key=MERGED_KEY)
        df = pd.read_csv(StringIO(response["Body"].read().decode("utf-8")))
        game_id = int(game_id)
        batter_id = int(batter_id)
        print("Looking for:", game_id, batter_id)


        # Clean/convert IDs to ensure they match
        df["game_id"] = df["game_id"].astype(int)
        df["batter_id"] = df["batter_id"].astype(int)

        row = df[(df["game_id"] == game_id) & (df["batter_id"] == batter_id)]
        if not row.empty:
            return round(row.iloc[0]["scaled_game_score"], 1)
        else:
            return None

    except Exception as e:
        print(f"Error loading game score: {e}")
        return None

# Generate the top banner
def generate_banner_section(pdf, hitter_name, game_date, player_id, team_name, position,game_id, Bats):
    """Generates a structured banner with a player's image, team logo, and centered text."""
    # Get opponent name
    opponent = load_player_opponent(game_id, team_name)

    #Hitter Game Score
    print(game_id)
    print(player_id)
    game_score = get_game_score_from_s3(game_id, player_id)
    print(game_score)
    # Dynamically get team color (fallback to dark gray if missing)
    team_color = TEAM_COLORS.get(team_name, "#333333")

    # Convert hex color to RGB
    team_color_rgb = tuple(int(team_color[i:i + 2], 16) for i in (1, 3, 5))

    # Set banner height
    banner_height = 35  # Reduce height to match the example
    margin = 10  # Margin for text and images

    # Draw background banner with team color
    pdf.set_fill_color(*team_color_rgb)
    pdf.rect(margin, margin, pdf.w - (2 * margin), banner_height, style="F")  # Apply margin to align visuals

    # Define standard image sizes
    headshot_size = 35  # Adjust to fit proportionally
    team_logo_size = 20  # Keep same size for consistency

    # Load player headshot
    player_headshot = fetch_player_headshot(player_id)
    if player_headshot:
        player_buf = BytesIO()
        player_headshot.save(player_buf, format="PNG")
        player_buf.seek(0)

        # Position headshot (left side, aligned vertically)
        headshot_x = margin + 5
        headshot_y = margin + (banner_height - headshot_size) / 2  # Center vertically
        pdf.image(player_buf, x=headshot_x, y=headshot_y, w=25, h=headshot_size)

    # Load team logo
    team_logo = fetch_team_logo(team_name)
    if team_logo:
        logo_buf = BytesIO()
        team_logo.save(logo_buf, format="PNG")
        logo_buf.seek(0)

        # Position team logo (right side, aligned vertically)
        logo_x = pdf.w - 30 - margin - 5  # Align to right
        logo_y = margin + (banner_height - team_logo_size) / 2  # Center vertically
        # Get original dimensions
        logo_width, logo_height = team_logo.size
        aspect_ratio = logo_width / logo_height

        # Define desired logo height
        desired_height = team_logo_size  # 20 pixels

        # Calculate width dynamically based on aspect ratio
        dynamic_width = desired_height * aspect_ratio

        # Adjust X position to keep logo aligned to the right
        logo_x = pdf.w - margin - dynamic_width - 5  # Adjusted for new width

        # Insert image preserving original aspect ratio
        pdf.image(logo_buf, x=logo_x, y=logo_y, w=dynamic_width, h=desired_height)

    # Center the text
    pdf.set_text_color(255, 255, 255)  # White text
    pdf.set_font("Times", "B", 20)

    # Player Name
    text_x = pdf.w / 2
    pdf.set_xy(text_x - 40, margin + 6)  # Adjust Y positioning
    pdf.cell(80, 8, hitter_name.upper(), align="C")

    # Game Date and Opponent
    pdf.set_font("Courier", "", 12)
    pdf.set_xy(text_x - 40, margin + 16)
    pdf.cell(80, 8, f"{game_date} vs. {opponent}", align="C")

    # Position and Throws Info
    pdf.set_font("Courier", "", 10)
    pdf.set_xy(text_x - 40, margin + 22)
    pdf.cell(80, 8, f"POSITION: {position.upper()} BATS: {Bats}", align="C")

    pdf.set_font("Courier", "", 10)
    pdf.set_xy(text_x - 40, margin + 26)
    pdf.cell(80, 8, f"GAME SCORE: {game_score}", align="C")





# Fetch Box Score for Game
def fetch_box_score_for_game_from_s3(game_id):
    box_scores = load_box_scores_from_s3()
    game_box_score = box_scores[box_scores["game_pk"].astype(str) == game_id]
    return game_box_score if not game_box_score.empty else None


from fpdf import FPDF, XPos, YPos
from io import BytesIO, StringIO
import matplotlib.pyplot as plt


class PDF(FPDF):
    def header(self):
        """Create header for the PDF with hitter name and date."""
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(255, 255, 255)  # White text
        self.set_fill_color(150, 0, 0)  # Red background
        self.cell(0, 12, f"{self.hitter_name} - {self.game_date}", align='C', fill=True, ln=True)

    def footer(self):
        """Create footer for the PDF with data source and stat explanations."""
        self.set_y(-15)  # Move to the bottom of the page
        self.set_font("Helvetica", "I", 6)  # Use an italic font for footer
        self.set_text_color(100, 100, 100)  # Gray text

        # Footer text: Data source & metric explanations
        footer_text = (
            "Data sourced from MLB StatsAPI | Photos from MLB | RE_ADDED = Run Expectancy Added | "
            "Leverage Value = Change in Expected Runs Due to Play Outcome | @jbaseball_viz"
        )

        self.cell(0, 10, footer_text, align="C")

    def add_matplotlib_figure(self, fig, x, y, w, h):
        """Embed a Matplotlib figure directly into the PDF."""
        buf = BytesIO()

        fig.savefig(buf, format="png", dpi=600, bbox_inches="tight")  # High DPI for clarity
        fig.tight_layout(pad=1.0)
        buf.seek(0)
        self.image(buf, x, y, w, h)


def generate_hitter_report_pdf(player_id, game_date):
    """Creates a structured, high-quality scouting report PDF for a hitter."""

    # Fetch data
    team_logos = load_team_logos_from_s3()
    hitter_name, position, Bats = fetch_player_name(player_id)
    if not hitter_name or not position:
        print(f"Missing player data for ID {player_id}. Skipping report generation.")
        return
    game_id = fetch_game_id(player_id, game_date)

    if not game_id:
        print(f" No game found for player {player_id} on {game_date}")
        return

    print(f" Found Game ID: {game_id}")
    box_score = fetch_box_score_for_game_from_s3(game_id)
    player_game_summary = box_score[box_score["player_id"] == player_id] if box_score is not None else None
    season_stats, _, team_name = fetch_hitter_stats_and_team(player_id)

    if season_stats is None:
        print(f" Missing season stats for player {player_id}")
    if player_game_summary is None or player_game_summary.empty:
        print(f" Missing game performance data for player {player_id}")

    if season_stats is None or player_game_summary is None or player_game_summary.empty:
        print(f" Cannot generate report due to missing data.")
        return

    print(f" Generating Visualizations...")

    #Generate visualizations
    try:
        game_perf_table = generate_hitter_game_performance_visual(player_id, game_id)
        print("Game Performance Table Generated")
    except Exception as e:
        print(f"Error in game performance table: {e}")
        game_perf_table = None

    try:
        rolling_chart = generate_and_plot_rolling_averages(player_id, return_fig=True)
        print("Rolling Averages Chart Generated")
    except Exception as e:
        print(f"Error in rolling averages chart: {e}")
        rolling_chart = None

    try:
        heatmap = generate_hitter_heatmap(player_id, hitter_name, game_id)
        print("Hitter Heatmap Generated")
    except Exception as e:
        print(f"Error in hitter heatmap: {e}")
        heatmap = None

    try:
        spray_chart = generate_spray_chart_visual(player_id, game_date)
        print("Spray Chart Generated")
    except Exception as e:
        print(f"Error in spray chart: {e}")
        spray_chart = None

    # Debugging - Ensure spray_chart is a Figure before adding to PDF
    if spray_chart is None:
        print(" Error: Spray chart visualization failed.")
    elif not isinstance(spray_chart, plt.Figure):
        print(f" Warning: Expected Figure but got {type(spray_chart)}")
        spray_chart = spray_chart.figure  # Convert Axes to Figure if needed

    try:
        season_table = visualize_recent_hitter_stats_table(season_stats, team_name, hitter_name, return_fig=True)
        print("Season Stats Table Generated")
    except Exception as e:
        print(f"Error in season stats table: {e}")
        season_table = None

    try:
        critical_table = generate_critical_moments_visual(game_id)
        print("Critical Moments Table Generated")
    except Exception as e:
        print(f"Error in critical moments table: {e}")
        critical_table = None

    #Generate PDF Layout
    pdf_width, pdf_height = 210, 240
    # Square layout for social media sharing
    pdf = PDF(orientation="P", unit="mm", format=(pdf_width, pdf_height))
    pdf.hitter_name = hitter_name
    pdf.game_date = game_date
    pdf.add_page()

    generate_banner_section(pdf, hitter_name, game_date, player_id, team_name, position,game_id,Bats)
    #Create player headshot

    # Adjust layout settings
    margin = 3
    full_width = pdf_width - (2 * margin)  # Tables aligned with the banner width
    third_width = (full_width - (2 * margin)) / 3  # Three visuals in a row
    row_height = 40  # Slightly increased for better fit
    pdf.set_text_color(0, 0, 0)  # Black text

    ### **Step 1: Position the Game Performance Table**
    y_pos = 30  # Adjusted position below the banner
    pdf.set_font("Courier", "B", 14)
    pdf.set_fill_color(255, 255, 255)  # Background fill to prevent overlap
    pdf.set_xy(margin, y_pos - 3)  # Move title closer to table


    # Insert Game Performance Table
    pdf.set_font("Courier", "B", 14)
    y_pos += 18  # Ensure spacing
    pdf.add_matplotlib_figure(game_perf_table, x=margin, y=y_pos, w=full_width, h=17)
    y_pos += row_height - 10  # Add extra space before next section

    ### **Step 2: Position the Visualizations**
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Courier", "B", 9)

    # Calculate X Positions for Centering
    rolling_chart_x = margin + (third_width / 2)
    heatmap_x = margin + third_width + (third_width / 2) + 3
    spray_chart_x = margin + (2 * third_width) + (third_width / 2) + 6

    # Titles Above Visualizations
    title_y_pos = y_pos - 8

    # Rolling Averages Title
    pdf.set_xy(rolling_chart_x - (third_width / 2), title_y_pos)
    pdf.cell(third_width, 8, f"{hitter_name} - Rolling Averages", align="C")

    # Heatmap Title
    pdf.set_xy(heatmap_x - (third_width / 2), title_y_pos)
    pdf.cell(third_width, 8, "Hitter Heatmap", align="C")

    # Spray Chart Title
    pdf.set_xy(spray_chart_x - (third_width / 2), title_y_pos)
    pdf.cell(third_width, 8, "Spray Chart", align="C")

    # Insert Visuals
    pdf.add_matplotlib_figure(rolling_chart, x=margin, y=y_pos, w=third_width, h=55)
    pdf.add_matplotlib_figure(heatmap, x=margin + third_width + 3, y=y_pos, w=third_width, h=55)
    pdf.add_matplotlib_figure(spray_chart, x=margin + (2 * third_width) + 6, y=y_pos, w=third_width, h=55)
    y_pos += row_height + 8  # Extra space for readability

    ### **Step 3: Adjust Position of Season Stats Table**
    y_pos += 8  # Move the entire section down more
    pdf.set_xy(margin, y_pos - 1)  # Title closer to table
    pdf.set_font("Courier", "B", 14)


    y_pos += 6  # Reduce spacing before the table
    pdf.add_matplotlib_figure(season_table, x=margin, y=y_pos, w=full_width, h=17)
    y_pos += row_height + 2  # Reduce spacing before the next section

    ### **Step 4: Adjust Position of Critical Moments Table**
    y_pos -= 22
    pdf.set_xy(margin, y_pos - 1)  # Title closer to table
    pdf.set_font("Courier", "B", 14)
    pdf.cell(full_width, 8, "Critical Moments Table", align="C")

    y_pos += 12  # Reduce spacing before the table
    pdf.add_matplotlib_figure(critical_table, x=margin, y=y_pos, w=full_width, h=row_height+8)
    y_pos += row_height + 3  # Reduce final spacing before footer


    #Save and Upload PDF
    output_path = f"/Users/joshsteckler/PycharmProjects/baseball-mvp/scripts/Hitter_Report_Card/Visualizations/Report_Card_Outputs/hitter_report_{hitter_name.replace(' ', '_')}_{game_date}.pdf"
    pdf.output(output_path)
    print(f"Report saved locally as {output_path}")

    s3_client = boto3.client("s3")
    filename = os.path.basename(output_path)  # e.g. hitter_report_Julio_Rodríguez_2025-03-29.pdf
    clean_filename = remove_accents(filename)
    s3_key = f"hitter_report_cards/{clean_filename}"
    s3_client = boto3.client("s3")
    s3_client.upload_file(output_path, S3_BUCKET, s3_key)
    s3_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}"
    print(f"Report uploaded to {s3_url}")

    return s3_url


# Example Run
if __name__ == "__main__":
    generate_hitter_report_pdf(player_id="671218", game_date="2025-05-06")
