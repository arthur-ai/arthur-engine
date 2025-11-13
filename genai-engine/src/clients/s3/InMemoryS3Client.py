import logging
from io import BytesIO

from fastapi import UploadFile

from clients.s3.abc_file_client import FileClient

logger = logging.getLogger()


class InMemoryClient(FileClient):
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def save_file(self, file_id: str, file: UploadFile) -> str:
        path = self.get_file_path("", file_id, file.filename or "")
        try:
            self.files[path] = file.file.read()
            return path
        except Exception as e:
            logger.error(f"Failed to save file to memory: {e}")
        return ""

    def read_file(self, key: str) -> UploadFile:
        file_bytes = BytesIO(self.files.get(key) or b"")
        size = file_bytes.getbuffer().nbytes
        return UploadFile(
            file=file_bytes,
            filename=self.get_file_name_from_path(key),
            size=size,
        )
