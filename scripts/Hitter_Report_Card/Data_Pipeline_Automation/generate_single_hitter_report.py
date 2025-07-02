import os
import psycopg2
from dotenv import load_dotenv
from scripts.Hitter_Report_Card.Visualizations.Hitter_Report_PDF import generate_hitter_report_pdf
import boto3

load_dotenv()

S3_BUCKET = "scouting-reports-bucket"
S3_PREFIX = "hitter_report_cards"

s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

def generate_single_hitter_report(player_name: str, game_date: str) -> str:
    conn = psycopg2.connect(os.getenv("DB_URL"))
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT key_mlbam FROM players
            WHERE LOWER(player_name) = LOWER(%s)
            LIMIT 1;
        """, (player_name,))
        result = cur.fetchone()
        if not result:
            raise ValueError(f"Player not found: {player_name}")

        player_id = str(result[0])
        generate_hitter_report_pdf(player_id=player_id, game_date=game_date)

        report_key = f"{S3_PREFIX}/{player_id}_{game_date}.pdf"
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": report_key},
            ExpiresIn=300
        )
        return url

    finally:
        cur.close()
        conn.close()
