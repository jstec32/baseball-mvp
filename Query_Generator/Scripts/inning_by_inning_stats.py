import pandas as pd
import requests, os, time
from io import BytesIO, StringIO
import boto3
from flask.cli import load_dotenv

load_dotenv()

s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-1")
)

S3_BUCKET = "baseball-data-mvp"
CSV_KEY = "mlb_game_data/team_game_stats_2025.csv"
BATCH_SIZE = 50

def fetch_json_with_retry(url, retries=3, delay=2):
    for attempt in range(retries):
        try:
            r = requests.get(url)
            r.raise_for_status()
            return r.json()
        except:
            time.sleep(delay)
    return None

def extract_runs_by_inning(linescore, side):
    innings = linescore.get("innings", [])
    runs_by_inning = []
    for i in range(9):
        if i < len(innings):
            runs = innings[i].get(side, {}).get("runs")
            runs_by_inning.append(runs if runs is not None else 0)
        else:
            runs_by_inning.append(0)
    return runs_by_inning

def extract_team_totals(linescore, side):
    side_data = linescore.get("teams", {}).get(side, {})
    return {
        "total_runs": side_data.get("runs"),
        "total_hits": side_data.get("hits"),
        "total_errors": side_data.get("errors")
    }

def process_batch(df, batch_game_pks):
    run_cols = [f"runs_inning_{i}" for i in range(1, 10)]
    total_cols = ["team_total_runs", "team_total_hits", "team_total_errors"]

    for game_pk in batch_game_pks:
        try:
            box = fetch_json_with_retry(f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore")
            line = fetch_json_with_retry(f"https://statsapi.mlb.com/api/v1/game/{game_pk}/linescore")
            if not box or not line:
                continue

            for side in ("home", "away"):
                box_team = box["teams"][side]["team"]["name"]
                runs_by_inning = extract_runs_by_inning(line, side)
                totals = extract_team_totals(line, side)

                mask = (df["game_pk"] == game_pk) & (
                    df["team_name"].str.strip().str.lower() == box_team.strip().lower()
                )
                if mask.sum() == 0:
                    continue

                for i in range(9):
                    df.loc[mask, f"runs_inning_{i+1}"] = runs_by_inning[i]
                df.loc[mask, "team_total_runs"] = totals["total_runs"]
                df.loc[mask, "team_total_hits"] = totals["total_hits"]
                df.loc[mask, "team_total_errors"] = totals["total_errors"]

        except Exception as e:
            print(f"Error processing game {game_pk}: {e}")
    return df

def update_csv_in_batches():
    obj = s3.get_object(Bucket=S3_BUCKET, Key=CSV_KEY)
    df = pd.read_csv(BytesIO(obj["Body"].read()))

    run_cols = [f"runs_inning_{i}" for i in range(1, 10)]
    total_cols = ["team_total_runs", "team_total_hits", "team_total_errors"]

    for col in run_cols + total_cols:
        if col not in df.columns:
            df[col] = None

    mask_missing = (df[run_cols].isnull().any(axis=1)) | (df[run_cols].sum(axis=1) == 0)
    missing_game_pks = df.loc[mask_missing, "game_pk"].unique()
    batches = [missing_game_pks[i:i + BATCH_SIZE] for i in range(0, len(missing_game_pks), BATCH_SIZE)]

    print(f"Total games to update: {len(missing_game_pks)}")
    print(f"Processing in {len(batches)} batches of up to {BATCH_SIZE} games each")

    for idx, batch in enumerate(batches):
        print(f"\nProcessing batch {idx + 1} of {len(batches)}: {len(batch)} game_pks")
        df = process_batch(df, batch)

    df["null_inning_count"] = df[run_cols].isnull().sum(axis=1)
    df = df.sort_values("null_inning_count").drop(columns=["null_inning_count"])
    df = df.drop_duplicates(subset=["game_pk", "team_name"], keep="first").reset_index(drop=True)

    buffer = StringIO()
    df.to_csv(buffer, index=False)
    s3.put_object(Bucket=S3_BUCKET, Key=CSV_KEY, Body=buffer.getvalue())
    print(f"\nFinal CSV saved to s3://{S3_BUCKET}/{CSV_KEY}")

update_csv_in_batches()









