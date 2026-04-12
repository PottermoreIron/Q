"""
S3-compatible storage client (works with MinIO locally, AWS S3 in production).
Uses boto3 under the hood; imported lazily.
"""

from __future__ import annotations

import uuid
from typing import BinaryIO

from config import settings


def _client():
    import boto3

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
    )


def upload_file(file_obj: BinaryIO, prefix: str = "uploads", suffix: str = ".csv") -> str:
    """Upload a file-like object. Returns the S3 key."""
    key = f"{prefix}/{uuid.uuid4()}{suffix}"
    _client().upload_fileobj(file_obj, settings.s3_bucket, key)
    return key


def download_bytes(key: str) -> bytes:
    """Download an object and return its raw bytes."""
    response = _client().get_object(Bucket=settings.s3_bucket, Key=key)
    return response["Body"].read()


def ensure_bucket() -> None:
    """Create the bucket if it doesn't exist (useful for MinIO dev setup)."""
    client = _client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
    except Exception:
        client.create_bucket(Bucket=settings.s3_bucket)
