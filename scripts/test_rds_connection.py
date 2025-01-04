import psycopg2

# Database connection details
host = "baseballmvp.czww6cykwaoo.us-east-2.rds.amazonaws.com"       # Replace with your RDS endpoint
database = "baseball_mvp"  # Replace with your database name
user = "admin1"           # Replace with your username
password = "RockCreek32!"       # Replace with your password

try:
    # Connect to RDS
    conn = psycopg2.connect(
        host=host,
        database=database,
        user=user,
        password=password
    )
    print("Connected to RDS successfully!")
    conn.close()
except Exception as e:
    print(f"Error connecting to RDS: {e}")
