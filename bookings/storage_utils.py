import datetime
from typing import Optional

from django.conf import settings
from django.core.files.storage import default_storage


def get_signed_url(file_field, expires_in: int = 300) -> Optional[str]:
    """
    Return a time-limited URL for a stored file.
    - If using S3 (boto3 available), generate a presigned URL.
    - Fallback to storage.url (may be public).
    """
    if not file_field:
        return None
    name = file_field.name
    storage = getattr(file_field, "storage", default_storage)
    # boto3 presign if available and storage has bucket attrs
    bucket = getattr(storage, "bucket_name", None) or getattr(settings, "AWS_STORAGE_BUCKET_NAME", None)
    s3_client = getattr(storage, "connection", None) and getattr(storage.connection, "meta", None)
    if bucket and s3_client:
        try:
            client = storage.connection.meta.client
            return client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": name},
                ExpiresIn=expires_in,
            )
        except Exception:
            pass
    try:
        return storage.url(name)
    except Exception:
        return name
