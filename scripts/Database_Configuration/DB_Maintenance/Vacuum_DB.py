import os

import psycopg2
import pandas as pd
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", 5432))  # Default port 5432 if not set
}

print(DB_CONFIG)
import psycopg2
import pandas as pd
from datetime import datetime
from tabulate import tabulate  # For clean console printing


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def check_table_size_and_bloat(table_name):
    query = """
        SELECT 
            pg_class.relname AS table_name,
            pg_size_pretty(pg_table_size(pg_class.oid)) AS table_size,
            pg_size_pretty(pg_total_relation_size(pg_class.oid)) AS total_size,
            pg_stat_user_tables.n_live_tup,
            pg_stat_user_tables.n_dead_tup,
            ROUND(
                (pg_stat_user_tables.n_dead_tup::NUMERIC / NULLIF(pg_stat_user_tables.n_live_tup + pg_stat_user_tables.n_dead_tup, 0)) * 100, 
                2
            ) AS dead_tuple_percent
        FROM pg_class
        JOIN pg_stat_user_tables 
        ON pg_class.oid = pg_stat_user_tables.relid
        WHERE pg_class.relname = %s;
    """

    with get_db_connection() as conn:
        df = pd.read_sql(query, conn, params=(table_name,))
    return df

def check_active_queries():
    query = """
    SELECT pid, now() - query_start AS duration, state, wait_event, query
    FROM pg_stat_activity
    WHERE state != 'idle' AND now() - query_start > interval '5 seconds'
    ORDER BY duration DESC;
    """
    with get_db_connection() as conn:
        df = pd.read_sql(query, conn)
    return df

def check_index_usage(table_name):
    query = """
    SELECT indexrelname AS index_name,
           idx_scan AS index_scans,
           pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
    FROM pg_stat_user_indexes
    WHERE relname = %s
    ORDER BY idx_scan ASC;
    """
    with get_db_connection() as conn:
        df = pd.read_sql(query, conn, params=(table_name,))
    return df

def check_autovacuum_activity(table_name):
    query = """
    SELECT relname, last_vacuum, last_autovacuum, last_analyze, last_autoanalyze
    FROM pg_stat_user_tables
    WHERE relname = %s;
    """
    with get_db_connection() as conn:
        df = pd.read_sql(query, conn, params=(table_name,))
    return df

def log_to_file(content):
    with open("health_check_log.txt", "a") as file:
        file.write(f"{datetime.now()} - {content}\n")

def run_full_health_check(table_name="pitch_data"):
    print(f"\n🔎 Running full health check for table: {table_name}")

    # 1. Check Table Size & Bloat
    table_stats = check_table_size_and_bloat(table_name)
    print("\n📊 Table Size & Bloat:")
    print(tabulate(table_stats, headers='keys', tablefmt='pretty'))
    log_to_file(f"Table Stats:\n{table_stats.to_string()}")

    # 2. Check Active Long-Running Queries
    queries = check_active_queries()
    print("\n⏱️ Active Long-Running Queries (>5 sec):")
    if queries.empty:
        print("✅ No long-running queries detected.")
    else:
        print(tabulate(queries, headers='keys', tablefmt='pretty'))
        log_to_file(f"Long Queries:\n{queries.to_string()}")

    # 3. Check Index Usage
    index_stats = check_index_usage(table_name)
    print("\n📑 Index Usage (scan counts & size):")
    print(tabulate(index_stats, headers='keys', tablefmt='pretty'))
    log_to_file(f"Index Stats:\n{index_stats.to_string()}")

    # 4. Check Autovacuum History
    autovacuum_stats = check_autovacuum_activity(table_name)
    print("\n🚀 Autovacuum & Analyze History:")
    print(tabulate(autovacuum_stats, headers='keys', tablefmt='pretty'))
    log_to_file(f"Autovacuum Stats:\n{autovacuum_stats.to_string()}")

    # 5. Diagnosis & Recommendations
    print("\n🩺 Diagnosis & Recommendations:")
    if not table_stats.empty:
        dead_tuple_percent = table_stats["dead_tuple_percent"].iloc[0]
        if dead_tuple_percent > 30:
            print(f"⚠️ High table bloat detected: {dead_tuple_percent}% dead tuples.")
            print("🔧 Recommendation: Run a VACUUM FULL ANALYZE on pitch_data during a maintenance window.")
        else:
            print(f"✅ Table bloat is under control: {dead_tuple_percent}% dead tuples.")

    if not queries.empty:
        print("⚠️ Long-running queries detected. Investigate them, especially if they scan the full table.")
    else:
        print("✅ No long-running queries detected.")

    if not autovacuum_stats.empty:
        last_auto = autovacuum_stats["last_autovacuum"].iloc[0]
        if pd.isnull(last_auto):
            print("⚠️ No autovacuum history found — autovacuum might be disabled.")
        else:
            print(f"✅ Last autovacuum ran at: {last_auto}")

    print("\n✅ Full health check complete — results also saved to health_check_log.txt")

if __name__ == "__main__":
    run_full_health_check()

import psycopg2
import pandas as pd
from tabulate import tabulate


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def fetch_active_queries():
    query = """
    SELECT datname, pid, usename, state, query_start, now() - query_start AS duration, query
    FROM pg_stat_activity
    WHERE state != 'idle'
    ORDER BY duration DESC;
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn)

def fetch_top_queries_from_statements():
    query = """
    SELECT query, calls, total_exec_time, mean_exec_time
    FROM pg_stat_statements
    ORDER BY total_exec_time DESC
    LIMIT 10;
    """
    with get_db_connection() as conn:
        return pd.read_sql(query, conn)

def analyze_query_usage():
    print("\n🔎 Checking Active Queries...")
    active_queries = fetch_active_queries()
    if active_queries.empty:
        print("✅ No active queries running longer than a few milliseconds.")
    else:
        print(tabulate(active_queries, headers='keys', tablefmt='pretty'))

    print("\n📊 Checking Top CPU-Consuming Queries (pg_stat_statements)...")
    top_queries = fetch_top_queries_from_statements()
    if top_queries.empty:
        print("✅ No recorded queries in pg_stat_statements.")
    else:
        print(tabulate(top_queries, headers='keys', tablefmt='pretty'))

if __name__ == "__main__":
    analyze_query_usage()

