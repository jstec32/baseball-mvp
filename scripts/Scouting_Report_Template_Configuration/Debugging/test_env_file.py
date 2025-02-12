from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

print("DB Host:", os.getenv("DB_HOST"))
print("AWS Access Key:", os.getenv("AWS_ACCESS_KEY_ID"))
print("S3 Bucket Name:", os.getenv("S3_BUCKET_NAME"))