import os
import boto3
import pandas as pd
from botocore.config import Config
from fastapi import FastAPI, Query
from pydantic import BaseModel
from pathlib import Path
from sqlalchemy.dialects.postgresql import psycopg2
from starlette.responses import StreamingResponse
from fastapi import Query
from dotenv import load_dotenv
import psycopg2
import requests
from Query_Generator.Scripts.Live_Game_Scores import fetch_mlb_scores
from Query_Generator.wrapper.llm_sql import ChatSession
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, HTTPException
from fastapi import Query
from fastapi.responses import JSONResponse
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from scripts.Hitter_Report_Card.Visualizations.Hitter_Report_PDF import generate_hitter_report_pdf

S3_BUCKET = "scouting-reports-bucket"
S3_REPORT_PREFIX = "hitter_report_cards"

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432))
}

s3_client = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-2"),
        config=Config(signature_version="s3v4")
    )
S3_LOG_BUCKET = "baseball-data-mvp"
S3_LOG_KEY = "logs/query_logs.jsonl"
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or use ["http://localhost:8081"] for tighter control
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
session = ChatSession(str(Path(__file__).parent / "sql_generation.txt"))

class QueryRequest(BaseModel):
    question: str
    output_format: str = "json"

@app.post("/query")
def ask_sql(request: QueryRequest):
    return session.query(request.question, request.output_format)

@app.get("/")
def root():
    return {"status": "Server running"}

@app.get("/generate_hitter_report")
def generate_hitter_report(player_id: str = Query(...), game_date: str = Query(...)):
    try:
        s3_url = generate_hitter_report_pdf(player_id=player_id, game_date=game_date)
        return {"success": True, "report_url": s3_url}
    except ClientError as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e.response['Error']['Message'])})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.get("/admin/logs")
def get_logs():
    try:
        obj = s3_client.get_object(Bucket=S3_LOG_BUCKET, Key=S3_LOG_KEY)
        logs = obj["Body"].read().decode("utf-8")
        # Return raw logs or parsed JSON
        return {"logs": logs}
    except s3_client.exceptions.NoSuchKey:
        return {"logs": ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/logs/download")
def download_logs():
    try:
        obj = s3_client.get_object(Bucket=S3_LOG_BUCKET, Key=S3_LOG_KEY)
        logs = obj["Body"].read()
        return StreamingResponse(
            iter([logs]),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="query_logs.jsonl"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/players/suggest")
def suggest_players(query: str = Query(...)):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        like_query = f"%{query.lower()}%"
        cur.execute("""
            SELECT player_name, key_mlbam
            FROM players
            WHERE LOWER(unaccent(player_name)) LIKE unaccent(%s)
            ORDER BY player_name
            LIMIT 10
        """, (like_query,))
        results = cur.fetchall()
        cur.close()
        conn.close()

        return {
            "players": [{"player_name": name, "key_mlbam": mid} for name, mid in results]
        }
    except Exception as e:
        return {"players": [], "error": str(e)}

@app.get("/live_scores")
def live_scores(date: str = Query(default=None)):
    try:
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        else:
            target_date = datetime.today().date()

        data = fetch_mlb_scores(date=target_date)  # your helper function
        return {"success": True, "games": data}

    except Exception as e:
        return {"success": False, "error": str(e)}


import traceback


import requests
import psycopg2
from fastapi.responses import JSONResponse

@app.get("/standings")
def get_division_standings():
    try:
        # Fetch standings from MLB API
        url = "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2025&standingsTypes=regularSeason"
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()

        # Parse team records
        records = []
        for league in data["records"]:
            for team in league["teamRecords"]:
                team_name = team["team"]["name"]
                league_record = team["leagueRecord"]
                records.append({
                    "team": team_name,
                    "wins": league_record["wins"],
                    "losses": league_record["losses"],
                    "pct": league_record["pct"],
                    "gb": team["gamesBack"],
                    "streak": team["streak"]["streakCode"]
                })

        standings_df = pd.DataFrame(records)

        # Query division info from database
        conn = psycopg2.connect(**DB_CONFIG)
        teams_df = pd.read_sql("SELECT name, division FROM teams;", conn)
        conn.close()

        # Merge and format
        merged_df = pd.merge(standings_df, teams_df, left_on="team", right_on="name", how="left")
        final_df = merged_df[["division", "team", "wins", "losses", "pct", "gb", "streak"]]
        final_df = final_df.sort_values(["division", "wins"], ascending=[True, False])

        # Group by division
        grouped = {}
        for division, group in merged_df.groupby("division"):
            grouped[division] = group.drop(columns="division").to_dict(orient="records")

        return JSONResponse(content={"success": True, "standings": grouped})

    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

