import os
import time
from datetime import datetime, timedelta

import boto3
import pandas as pd
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
from scripts.Hitter_Report_Card.Visualizations.Hitter_Report_PDF import generate_hitter_report_pdf

# Load credentials from .env.local
load_dotenv()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = "baseball-data-mvp"
MERGED_KEY = "mlb_game_data/merged_pitch_box_scores_2025.csv"

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

TEMP_CSV_PATH = "merged_pitch_box_scores_2025.csv"  # Local temp file



def download_merged_file_from_s3():
    print("Downloading merged file from S3")
    s3 = boto3.client("s3", aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)

    try:
        s3.download_file(AWS_BUCKET_NAME, MERGED_KEY, TEMP_CSV_PATH)
        print("File downloaded successfully.")
    except Exception as e:
        raise RuntimeError(f"Failed to download file from S3: {e}")



def get_top_10_performers(path, target_date=None):
    df = pd.read_csv(path)

    # Drop rows where game_date is missing
    df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce")

    if target_date is None:
        target_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    target_dt = pd.to_datetime(target_date)
    df = df[df["game_date"].dt.date == target_dt.date()]

    top_10 = df.sort_values("scaled_game_score", ascending=False).head(10)

    return top_10[["name", "team", "scaled_game_score", "game_id", "game_date", "batter_id"]]


def send_email(df, target_date=None):
    if target_date is None:
        today_str = datetime.today().strftime("%B %d, %Y")
    else:
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        today_str = target_date.strftime("%B %d, %Y")

    msg = EmailMessage()
    msg["Subject"] = f"Top 10 Game Score Performers ({today_str})"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECIPIENT_EMAIL

    table_html = df.to_html(index=False)
    msg.set_content("Attached are today's top 10 hitters by game score.")
    msg.add_alternative(f"""
    <html>
        <body>
            <h2>Top 10 Game Score Performers for {today_str}</h2>
            {table_html}
        </body>
    </html>
    """, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
        print(f"Email sent for {today_str}!")


import os

def run_top_performers_email_pipeline(target_date=None):
    log = ["Running Top Performers Email Pipeline"]

    try:
        download_merged_file_from_s3()
        log.append("Merged CSV downloaded from S3")

        top_10_df = get_top_10_performers(TEMP_CSV_PATH, target_date=target_date)

        if top_10_df.empty:
            log.append(f"No top performers found for {target_date}")
        else:
            log.append(f"Top 10 performers selected for {top_10_df.shape[0]} entries")
            send_email(top_10_df, target_date)
            generate_reports_for_top_hitters(top_10_df, target_date=target_date)
            log.append("Reports and email sent successfully")

    except Exception as e:
        error_msg = f"Error during top performers pipeline: {e}"
        print(error_msg)
        log.append(error_msg)

    finally:
        if os.path.exists(TEMP_CSV_PATH):
            os.remove(TEMP_CSV_PATH)
            log.append(f"Temp file deleted: {TEMP_CSV_PATH}")

    final_log = "\n".join(log)
    print(final_log)
    return log

from pdf2image import convert_from_path

def generate_reports_for_top_hitters(top_10_df, target_date=None):
    if target_date is None:
        target_date = (datetime.today() - timedelta(days=1)).date()
    folder_path = f"/Users/joshsteckler/PycharmProjects/baseball-mvp/scripts/Hitter_Report_Card/Log_Files/{target_date}"
    os.makedirs(folder_path, exist_ok=True)

    for _, row in top_10_df.iterrows():
        player_id = str(row["batter_id"])
        game_date = row["game_date"].strftime("%Y-%m-%d")

        try:
            generate_hitter_report_pdf(player_id=player_id, game_date=game_date)

            hitter_name = row["name"].replace(" ", "_")
            pdf_filename = f"hitter_report_{hitter_name}_{game_date}.pdf"
            old_path = f"/Users/joshsteckler/PycharmProjects/baseball-mvp/scripts/Hitter_Report_Card/Visualizations/Report_Card_Outputs/{pdf_filename}"
            new_path = os.path.join(folder_path, pdf_filename)

            if os.path.exists(old_path):
                os.rename(old_path, new_path)
                print(f"Moved report to: {new_path}")

                # Convert PDF to PNG
                images = convert_from_path(new_path, dpi=300)
                png_path = os.path.join(folder_path, f"{hitter_name}_{game_date}.png")
                images[0].save(png_path, "PNG")
                print(f"PNG saved to: {png_path}")

            else:
                print(f"Report not found: {old_path}")

        except Exception as e:
            print(f"Error generating report for {row['name']}: {e}")


run_top_performers_email_pipeline('2025-04-28')