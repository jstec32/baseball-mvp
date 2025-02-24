import psycopg2
from dotenv import load_dotenv
from psycopg2 import OperationalError

import os
load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432))  # Default port 5432 if not set
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
