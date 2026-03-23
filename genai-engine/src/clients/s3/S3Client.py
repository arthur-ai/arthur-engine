import logging
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile

from clients.s3.abc_file_client import FileClient

logger = logging.getLogger()


class S3Client(FileClient):
    def __init__(
        self,
        bucket_name: str,
        assumable_role_arn: str,
        prefix: str = "arthur_chat_assets",
    ) -> None:
        self.bucket_name = bucket_name
        self.role_arn = assumable_role_arn
        self.prefix = prefix

    def get_credentials(self) -> tuple[str, str, str]:
        sts_client = boto3.client("sts")
        assumed_role_session = sts_client.assume_role(
            RoleArn=self.role_arn,
            RoleSessionName="ArthurChatFileOperation",
        )
        creds = assumed_role_session["Credentials"]
        return creds["AccessKeyId"], creds["SecretAccessKey"], creds["SessionToken"]

    def save_file(self, file_id: str, file: UploadFile) -> str:
        try:
            key, secret, token = self.get_credentials()
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=key,
                aws_secret_access_key=secret,
                aws_session_token=token,
            )
            file_path = self.get_file_path(self.prefix, file_id, file.filename or "")
            s3_client.upload_fileobj(file.file, self.bucket_name, file_path)
            return file_path
        except ClientError as e:
            logger.error(e.response)
            if e.response["Error"]["Code"] == "AccessDenied":
                raise HTTPException(
                    status_code=403,
                    detail=e.response["Error"]["Message"],
                )
            elif e.response["Error"]["Code"] == "NoSuchEntity":
                raise HTTPException(
                    status_code=404,
                    detail=e.response["Error"]["Message"],
                )
            else:
                raise HTTPException(status_code=403, detail=f"An error occurred: {e}")
        except Exception as e:
            raise e

    def read_file(self, file_path: str) -> UploadFile:
        try:
            key, secret, token = self.get_credentials()
            assumed_session = boto3.Session(
                aws_access_key_id=key,
                aws_secret_access_key=secret,
                aws_session_token=token,
            )

            s3 = assumed_session.resource("s3")
            obj = s3.Object(self.bucket_name, file_path)
            file_content = obj.get()["Body"].read()
            return UploadFile(
                file=BytesIO(file_content),
                filename=self.get_file_name_from_path(obj.key),
                size=obj.content_length,
            )
        except ClientError as e:
            logger.error(e.response)
            if e.response["Error"]["Code"] == "AccessDenied":
                raise HTTPException(
                    status_code=403,
                    detail=e.response["Error"]["Message"],
                )
            elif e.response["Error"]["Code"] == "NoSuchEntity":
                raise HTTPException(
                    status_code=403,
                    detail=e.response["Error"]["Message"],
                )
            else:
                raise HTTPException(status_code=403, detail=f"An error occurred: {e}")
        except Exception as e:
            raise e
