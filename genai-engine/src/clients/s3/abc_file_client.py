from abc import ABC, abstractmethod

from fastapi import UploadFile


class FileClient(ABC):
    @abstractmethod
    def read_file(self, file_path: str) -> UploadFile:
        raise NotImplementedError

    @abstractmethod
    def save_file(self, file_id: str, file: UploadFile) -> str:
        raise NotImplementedError

    def get_file_path(self, prefix: str, file_id: str, file_name: str) -> str:
        path_seq = [prefix, file_id, file_name]
        path_seq = [e for e in path_seq if e and len(e) > 0]
        return "/".join(path_seq)

    def get_file_name_from_path(self, path: str) -> str:
        return str.split(path, "/")[-1]
