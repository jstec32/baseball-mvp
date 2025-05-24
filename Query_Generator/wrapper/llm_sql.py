import os
import json
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
    def __init__(self):
        self.schema = load_schema_from_s3()

    def ask_sql(self, user_q: str) -> str:
        schema_str = json.dumps(self.schema)
        prompt = (
            f"You are a SQL generator. Only use these tables and columns. Columns used in the sql statement must exist in the following tables given here:\n{schema_str}\n\n"
            f"Generate a single, read-only SELECT statement (no semicolons, no comments) to answer. Ensure you use consistent structure in all of your responses and statements should be the same result everytime.:\n\"{user_q}\""
        )
        resp = llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}]
        )
        # strip any backticks or quotes
        raw_sql = resp.choices[0].message.content
        print("\n=== LLM raw response ===\n", raw_sql, "\n=== end raw response ===\n")
        return raw_sql.strip().strip("```sql").strip("```")

    def validate_sql(self, sql: str):
        # Must be a single statement
        parsed = sqlparse.parse(sql)
        if len(parsed) != 1:
            raise ValueError("Only one SQL statement is allowed.")
        stmt = parsed[0]
        # Must be a SELECT
        if stmt.get_type().upper() != "SELECT":
            raise ValueError("Only SELECT queries are allowed.")
        forbidden = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"}
        tokens = [t for t in stmt.tokens if t.ttype is None]  # identifiers & keywords
        text = stmt.value.upper()
        for kw in forbidden:
            if kw in text:
                raise ValueError(f"Forbidden keyword in query: {kw}")
        return True

    def run(self, user_q: str, output_format: str = "json"):
        sql = self.ask_sql(user_q)
        self.validate_sql(sql)

        conn = psycopg2.connect(**DB_CONFIG)
        cur  = conn.cursor()
        cur.execute(sql)
        rows    = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        if output_format == "csv":
            import io, csv
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(columns)
            writer.writerows(rows)
            return buf.getvalue()

        return {"sql": sql, "columns": columns, "rows": rows}

# Quick manual test
if __name__ == "__main__":
    sandbox = SQLSandbox()
    example = "Show me Gerrit Cole's monthly ERA during the 2025 season."
    result  = sandbox.run(example)
    print(json.dumps(result, indent=2))
