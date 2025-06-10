import os
import json
from io import BytesIO
from pathlib import Path
import re

from jinja2 import Template
import boto3
import sqlparse
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv
import duckdb
import pandas as pd
from sqlalchemy import create_engine
load_dotenv()
from datetime import datetime, timezone
import json
import io, csv
import logging


# S3 & Schema
S3_BUCKET = "baseball-data-mvp"
S3_KEY    = "query_wrapper/2025_schema.json"
os.environ["RUNNING_LOCALLY"] = "true"

def load_schema_from_s3() -> dict:
    s3 = boto3.client(
        "s3",
        aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name           = os.getenv("AWS_REGION", "us-east-1")
    )
    obj = s3.get_object(Bucket=S3_BUCKET, Key=S3_KEY)
    return json.loads(obj["Body"].read())

# Postgres config
DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port":     int(os.getenv("DB_PORT", 5432)),
}

CSV_SOURCES = {
    "merged_pitch_box_scores_2025": "mlb_game_data/merged_pitch_box_scores_2025.csv",
    "mlb_game_data_2025":            "mlb_game_data/mlb_game_data_2025.csv",
    "team_game_stats_2025": "mlb_game_data/team_game_stats_2025.csv"
}

# Configure the JSON logger
logger = logging.getLogger("sql_chat")
logger.setLevel(logging.INFO)
fh = logging.FileHandler("sql_chat.log", encoding="utf-8")
fh.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(fh)
logging.getLogger(__name__).addHandler(fh)
logging.getLogger(__name__).setLevel(logging.INFO)

# OpenAI client
llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class SQLSandbox:
    def __init__(self, template_path: str):
        # 1) load the dynamic schema and your Jinja prompt template
        self.schema   = load_schema_from_s3()
        tpl_text      = Path(template_path).read_text()
        self.template = Template(tpl_text)

        # 2) prepare a SQLAlchemy engine for Postgres → Pandas pulls
        pg_url = (
            f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
            f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        )
        self.pg_engine = create_engine(pg_url)

        # 3) keep the CSV→S3 mappings and an S3 client
        self.csv_sources = CSV_SOURCES
        self.s3         = boto3.client(
            "s3",
            aws_access_key_id     = os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name           = os.getenv("AWS_REGION", "us-east-1")
        )

    def ask_sql(self, user_q: str) -> str:

        prompt = self.template.render(
            schema     = json.dumps(self.schema, indent=2),
            user_query = user_q
        )
        resp = llm_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role":"system","content":prompt}]
        )
        raw_sql = resp.choices[0].message.content
        print("\n=== LLM raw response ===\n", raw_sql, "\n=== end raw response ===\n")
        return raw_sql.strip().strip("```sql").strip("```")

    def modify_sql(self, prev_sql: str, edit_instruction: str) -> str:
        """Patch an existing SQL per a follow‑up instruction."""
        patch_prompt = (
            f"Here is an existing SQL query:\n{prev_sql}\n\n"
            f"Modify it so that it also {edit_instruction}.\n"
            "Only output the new, valid SELECT statement."
        )
        resp = llm_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role":"system","content":patch_prompt}]
        )
        patched = resp.choices[0].message.content
        return patched.strip().strip("```sql").strip("```")

    def validate_sql(self, sql: str):
        """Ensure it’s a single, read‑only SELECT."""
        parsed = sqlparse.parse(sql)
        if len(parsed) != 1:
            raise ValueError("Only one SQL statement is allowed.")
        stmt = parsed[0]
        if stmt.get_type().upper() != "SELECT":
            raise ValueError("Only SELECT queries are allowed.")
        forbidden = {"INSERT","UPDATE","DELETE","DROP","ALTER","CREATE"}
        text = stmt.value.upper()
        for kw in forbidden:
            if kw in text:
                raise ValueError(f"Forbidden keyword in query: {kw}")

    def execute(self, sql: str):
        sql_lower = sql.lower()
        use_duck = any(tbl in sql_lower for tbl in self.csv_sources)

        if use_duck:
            # ——— Run in DuckDB ———
            con = duckdb.connect()

            # 1) load each CSV from S3 into a DataFrame & register
            for tbl, s3_key in self.csv_sources.items():
                obj = self.s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
                df_csv = pd.read_csv(BytesIO(obj["Body"].read()))

                if "game_date" in df_csv.columns:
                    # 1a) coerce invalid strings to NaT, infer formats for speed
                    df_csv["game_date"] = pd.to_datetime(
                        df_csv["game_date"],
                        errors="coerce",
                        infer_datetime_format=True
                    )
                    # 1b) fill any NaT with 2025‑04‑01
                    n_missing = df_csv["game_date"].isna().sum()
                    if n_missing:
                        print(f"Info: filling {n_missing} missing game_date rows in '{tbl}' with 2025-04-01")
                        df_csv["game_date"].fillna(pd.Timestamp("2025-04-01"), inplace=True)

                con.register(tbl, df_csv)

            # 2) pull your core Postgres tables into Pandas & register
            for table in ["pitcher_game_logs", "hitter_season_statistics", "players", "teams"]:
                df = pd.read_sql(f"SELECT * FROM {table}", self.pg_engine)
                con.register(table, df)

            # 3) execute the query in DuckDB
            df_res = con.execute(sql).df()
            return list(df_res.columns), df_res.values.tolist()

        # ——— Fallback: run in Postgres ———
        conn = psycopg2.connect(**DB_CONFIG)
        cur  = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()
        return cols, rows


# ────── ChatSession for back and forth ──────
logger = logging.getLogger(__name__)

class ChatSession:
    def __init__(self, template_path: str):
        self.sb      = SQLSandbox(template_path)
        self.history = []
        self.last_q  = ""

    def _is_followup(self, last_q: str, user_q: str) -> bool:
        clf_prompt = f"""
You are a classifier. Given a previous question and a new question, answer ONLY “FOLLOWUP”
if the new one modifies or extends the previous; otherwise answer “NEW”.

Examples:
Previous: "Show Gerrit Cole’s monthly ERA."
New:      "Also include his strikeouts."    → FOLLOWUP
---
Previous: "Show Gerrit Cole’s monthly ERA."
New:      "Who leads MLB in ERA this season?" → NEW
---
Previous: "{last_q}"
New:      "{user_q}"
Answer:
"""
        resp = llm_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role":"system","content":clf_prompt}]
        )
        return resp.choices[0].message.content.strip().upper() == "FOLLOWUP"

    def query(self, user_q: str, output_format: str = "json"):
        # Auto-detect CSV request from phrasing
        if output_format == "json" and ("csv" in user_q.lower() or "download" in user_q.lower()):
            output_format = "csv"

        # Detect follow-up vs. new question
        if self.last_q and self._is_followup(self.last_q, user_q):
            use_patch = True
        else:
            use_patch = False
            self.history.clear()
        self.last_q = user_q

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_query": user_q,
            "attempts": []
        }

        # SQL generation
        try:
            sql = self.sb.modify_sql(self.history[-1]["sql"], user_q) if use_patch else self.sb.ask_sql(user_q)
            self.sb.validate_sql(sql)
        except Exception as ve:
            entry["attempts"].append({"sql": sql, "error": str(ve)})
            logger.info(json.dumps(entry))
            return {
                "success": False,
                "error": "Sorry, I couldn’t generate a valid SQL query for that request.",
                "attempts": entry["attempts"]
            }

        # SQL execution with 1 retry
        cols, rows = [], []
        final_error = None
        for attempt in (1, 2):
            try:
                cols, rows = self.sb.execute(sql)
                entry.update({
                    "final_sql": sql,
                    "columns": cols,
                    "row_count": len(rows)
                })
                break
            except Exception as err:
                err_msg = str(err).split("\n", 1)[0]
                entry["attempts"].append({"sql": sql, "error": err_msg})
                final_error = err_msg

                if attempt == 1:
                    try:
                        sql = self.sb.modify_sql(sql, f"Error: {err_msg}. Please fix the SQL.")
                        self.sb.validate_sql(sql)
                    except Exception as patch_err:
                        final_error = str(patch_err).split("\n", 1)[0]
                        entry["attempts"].append({"sql": sql, "error": final_error})
                        break
                else:
                    break

        logger.info(json.dumps(entry))

        # On failure
        if not cols and final_error:
            return {
                "success": False,
                "error": "We don’t have the appropriate data to satisfy that request right now.",
                "attempts": entry["attempts"]
            }

        # Success
        self.history.append({"sql": sql, "cols": cols, "rows": rows})

        # CSV output
        if output_format == "csv":
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(cols)
            writer.writerows(rows)

            if os.getenv("RUNNING_LOCALLY", "true").lower() == "true":
                download_path = Path.home() / "Downloads" / "query_results.csv"
                with open(download_path, "w", newline="") as f:
                    f.write(buf.getvalue())
                print(f"\nCSV saved to {download_path}\n")
                return {
                    "success": True,
                    "columns": cols,
                    "rows": rows,
                    "sql": sql,
                    "csv_download_path": str(download_path)
                }

            return {
                "success": True,
                "columns": cols,
                "rows": rows,
                "sql": sql,
                "csv_download_buffer": buf.getvalue()
            }

        # Web output
        if output_format == "web":
            return {
                "success": True,
                "sql": sql,
                "columns": cols,
                "rows": [dict(zip(cols, row)) for row in rows]
            }

        # JSON default
        return {
            "success": True,
            "columns": cols,
            "rows": rows,
            "sql": sql,
            "csv_download_path": None
        }

if __name__ == "__main__":
    import pandas as pd

    prompt_file = Path(__file__).parent / "sql_generation.txt"
    session     = ChatSession(str(prompt_file))

    print("Welcome to the SQL chat. Type your question, or ‘quit’ to exit.")
    while True:
        user_q = input("You ▶ ")
        if user_q.lower() in ("quit", "exit"):
            break

        result = session.query(user_q)

        # Handle friendly errors
        if "error" in result:
            print("\n " + result["error"] + "\n")
            continue

        # Otherwise we have a successful result
        df = pd.DataFrame(result["rows"], columns=result["columns"])
        print("\nResult:\n")
        print(df.to_string(index=False))
        print("\n")