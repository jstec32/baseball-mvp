import boto3
from pybaseball import statcast
import pandas as pd

# Step 1: Fetch baseball data
print("Fetching baseball data...")
data = statcast('2023-10-04')  # Adjust dates as needed
print("Data fetched successfully!")

# Step 2: Save the data locally
file_name = "statcast_2023.csv"
data.to_csv(file_name, index=False)
print(f"Data saved locally as {file_name}")

# Step 3: Upload the data to S3
print("Uploading data to S3...")
s3 = boto3.client('s3')
bucket_name = "baseball-data-mvp"  # Replace with your S3 bucket name
s3.upload_file(file_name, bucket_name, f"data/{file_name}")
print("Data uploaded to S3 successfully!")
