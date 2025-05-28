import os
import boto3
from dotenv import load_dotenv
from validation.validation import aws_validation
from io import BytesIO

load_dotenv()

s3_client = boto3.client(
    service_name='s3',
    region_name=os.getenv('AWS_REGION'),
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
)

BUCKET_NAME = os.getenv('AWS_S3_BUCKET_NAME')

@aws_validation
def save_file_in_s3(buffer, object_key):
    """
    Upload a file-like object to an S3 bucket.
    """
    s3_client.upload_fileobj(buffer, BUCKET_NAME, object_key)


@aws_validation
def get_file_s3(object_key):
    """
    Download an object from an S3 bucket into a BytesIO buffer.
    """
    buffer = BytesIO()
    s3_client.download_fileobj(BUCKET_NAME, object_key, buffer)
    buffer.seek(0)
    return buffer


@aws_validation
def delete_file_s3(object_key):
    """
    Delete an object from an S3 bucket.
    """
    s3_client.delete_object(Bucket=BUCKET_NAME, Key=object_key)
