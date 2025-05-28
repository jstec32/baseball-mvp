import os
import json
from pathlib import Path
from jinja2 import Template
import boto3
import sqlparse
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# S3 & Schema
S3_BUCKET = "baseball-data-mvp"
S3_KEY    = "query_wrapper/2025_schema.json"

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

# OpenAI client
llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class SQLSandbox:
    def __init__(self, template_path: str):
        self.schema = load_schema_from_s3()
        tpl_text    = Path(template_path).read_text()
        self.template = Template(tpl_text)

    def ask_sql(self, user_q: str) -> str:
        prompt = self.template.render(
            schema     = json.dumps(self.schema, indent=2),
            user_query = user_q
        )
        resp = llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":prompt}]
        )
        raw_sql = resp.choices[0].message.content
        print("\n=== LLM raw response ===\n", raw_sql, "\n=== end raw response ===\n")
        return raw_sql.strip().strip("```sql").strip("```")

    def modify_sql(self, prev_sql: str, edit_instruction: str) -> str:
        """
        Take an existing SELECT and modify it per the user's follow-up.
        """
        patch_prompt = (
            f"Here is an existing SQL query:\n{prev_sql}\n\n"
            f"Modify it so that it also {edit_instruction}.\n"
            "Only output the new, valid SELECT statement."
        )
        resp = llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":patch_prompt}]
        )
        patch_sql = resp.choices[0].message.content
        return patch_sql.strip().strip("```sql").strip("```")

    def validate_sql(self, sql: str):
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
        return True

    def execute(self, sql: str):
        conn = psycopg2.connect(**DB_CONFIG)
        cur  = conn.cursor()
        cur.execute(sql)
        rows    = cur.fetchall()
        cols    = [d[0] for d in cur.description]
        cur.close()
        conn.close()
        return cols, rows

    def run(self, user_q: str, output_format: str = "json"):
        raise RuntimeError("Use ChatSession for multi-turn. For single statements, call .execute() directly.")

class ChatSession:
    def __init__(self, template_path: str):
        self.sb      = SQLSandbox(template_path)
        self.history = []  # each entry is {"sql":..., "cols":..., "rows":...}

    def query(self, user_q: str, output_format: str = "json"):
        # first turn = generate; next turns = patch
        if not self.history:
            sql = self.sb.ask_sql(user_q)
        else:
            prev_sql = self.history[-1]["sql"]
            sql      = self.sb.modify_sql(prev_sql, user_q)

        self.sb.validate_sql(sql)
        cols, rows = self.sb.execute(sql)
        self.history.append({"sql":sql,"cols":cols,"rows":rows})

        if output_format == "csv":
            import io, csv
            buf    = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(cols)
            writer.writerows(rows)
            return buf.getvalue()

        return {"sql":sql,"columns":cols,"rows":rows}

if __name__ == "__main__":
    import pandas as pd

    prompt_file = "/Users/joshsteckler/PycharmProjects/baseball-mvp/Query_Generator/wrapper/sql_generation.txt"
    session     = ChatSession(prompt_file)

    print("Welcome to the SQL chat. Type your question, or ‘quit’ to exit.")
    while True:
        user_q = input("You ▶ ")
        if user_q.lower() in ("quit","exit"):
            break

        result = session.query(user_q)
        # build a dataframe from the latest result
        df = pd.DataFrame(result["rows"], columns=result["columns"])
        print("\nResult:\n")
        print(df.to_string(index=False))
        print("\n")