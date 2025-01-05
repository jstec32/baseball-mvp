import boto3

s3 = boto3.client('s3')

bucket_name = "baseball-data-mvp"  # Replace with your bucket name
file_name = "../test_s3.txt"
s3.upload_file(file_name, bucket_name, "test_s3.txt")

print("File uploaded to S3")
