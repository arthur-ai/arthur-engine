from io import BytesIO

from azure.storage.blob import BlobServiceClient
from fastapi import UploadFile

from clients.s3.abc_file_client import FileClient


class AzureBlobStorageClient(FileClient):
    def __init__(
        self,
        storage_account_connection_string: str,
        container_name: str,
        prefix="arthur_chat_assets",
    ):
        self.prefix = prefix

        blob_service_client = BlobServiceClient.from_connection_string(
            storage_account_connection_string,
        )
        self.container_client = blob_service_client.get_container_client(container_name)

    def save_file(self, file_id: str, file: UploadFile):
        file_path = self.get_file_path(self.prefix, file_id, file.filename)
        blob_client = self.container_client.get_blob_client(file_path)

        with file.file as f:
            blob_client.upload_blob(f, overwrite=True)
        return file_path

    def read_file(self, file_path: str):
        blob_client = self.container_client.get_blob_client(file_path)
        data = blob_client.download_blob()

        return UploadFile(
            file=BytesIO(data.readall()),
            filename=self.get_file_name_from_path(blob_client.blob_name),
            size=blob_client.get_blob_properties().size,
        )
