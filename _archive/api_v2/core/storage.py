import io
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
from typing import Optional

from ..config.config import settings

class MinioClient:
    def __init__(self):
        # boto3 requires the endpoint_url to connect to MinIO instead of AWS S3
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.MINIO_URL,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            # Bỏ qua SSL (http thay vì https)
            use_ssl=False, 
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            # 404 means the bucket does not exist
            error_code = e.response['Error']['Code']
            if error_code == '404':
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            else:
                raise

    def upload_file(self, file: UploadFile, object_name: str) -> str:
        """
        Uploads a file directly to MinIO.
        Returns the MinIO object name (key).
        """
        self.s3_client.upload_fileobj(
            file.file,
            self.bucket_name,
            object_name,
            ExtraArgs={'ContentType': file.content_type}
        )
        return object_name

    def download_file_bytes(self, object_name: str) -> bytes:
        """
        Download a file from MinIO into memory (bytes).
        """
        stream = io.BytesIO()
        self.s3_client.download_fileobj(self.bucket_name, object_name, stream)
        stream.seek(0)
        return stream.read()

# Khởi tạo Singleton client
minio_client = MinioClient()
