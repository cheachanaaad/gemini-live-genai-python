import logging
from pathlib import Path

from google.cloud import storage

logger = logging.getLogger(__name__)


class JsonStorageTarget:
    def __init__(self, location):
        self.location = str(location)
        self.is_gcs = self.location.startswith("gs://")
        self.path = None
        self.bucket_name = None
        self.blob_name = None
        self.client = None

        if self.is_gcs:
            bucket_and_blob = self.location[5:]
            bucket_name, _, blob_name = bucket_and_blob.partition("/")
            if not bucket_name or not blob_name:
                raise ValueError(f"Invalid GCS path: {self.location}")
            self.bucket_name = bucket_name
            self.blob_name = blob_name
            self.client = storage.Client()
        else:
            self.path = Path(self.location)
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def exists(self):
        if self.is_gcs:
            return self.client.bucket(self.bucket_name).blob(self.blob_name).exists()
        return self.path.exists()

    def read_text(self):
        if self.is_gcs:
            blob = self.client.bucket(self.bucket_name).blob(self.blob_name)
            return blob.download_as_text(encoding="utf-8")
        return self.path.read_text(encoding="utf-8")

    def write_text(self, content):
        if self.is_gcs:
            blob = self.client.bucket(self.bucket_name).blob(self.blob_name)
            blob.upload_from_string(content, content_type="application/json")
            return
        self.path.write_text(content, encoding="utf-8")

    def describe(self):
        return self.location
