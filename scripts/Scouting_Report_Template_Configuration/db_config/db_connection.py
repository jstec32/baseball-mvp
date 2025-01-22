import psycopg2
from psycopg2 import OperationalError

# Supabase connection details
DB_CONFIG = {
    "host": "aws-0-us-east-2.pooler.supabase.com",
    "database": "postgres",
    "user": "postgres.chcovbrcpmlxyauansqe",
    "password": "1Z4IO6fxxYw8PgxL",  # Replace with your Supabase password
    "port": 5432  # Default PostgreSQL port
}

def get_db_connection():
    """
    Establish and return a connection to the Supabase PostgreSQL database.
    :return: psycopg2 connection object
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Connected to Supabase PostgreSQL database successfully!")
        return conn
    except OperationalError as e:
        print(f"Error connecting to Supabase: {e}")
        return None


import gc

def clear_memory():
    """
    Clears memory and cache to reduce usage.
    Works for general Python objects.
    """
    try:
        # Clear the garbage collector
        gc.collect()
        print("Garbage collector cleared.")
    except Exception as e:
        print(f"An error occurred while clearing memory: {e}")
