import psycopg2
from psycopg2 import OperationalError

# Supabase connection details
host = "aws-0-us-east-2.pooler.supabase.com"
database = "postgres"
user = "postgres.chcovbrcpmlxyauansqe"
password = "1Z4IO6fxxYw8PgxL"  # Replace with your Supabase password
port = 5432  # Default PostgreSQL port

try:
    # Connect to Supabase
    conn = psycopg2.connect(
        host=host,
        database=database,
        user=user,
        password=password,
        port=port
    )
    print("Connected to Supabase PostgreSQL database successfully!")
    conn.close()
except OperationalError as e:
    print(f"Error connecting to Supabase: {e}")

try:
    # Connect to Supabase
    conn = psycopg2.connect(
        host=host,
        database=database,
        user=user,
        password=password,
        port=port
    )
    cursor = conn.cursor()
    # Test query
    cursor.execute("SELECT current_date;")
    result = cursor.fetchone()
    print(f"Query result: {result}")
    cursor.close()
    conn.close()
except OperationalError as e:
    print(f"Error connecting to Supabase: {e}")

