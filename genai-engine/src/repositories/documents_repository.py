import uuid
from unittest.mock import MagicMock

from clients.s3.S3Client import S3Client
from db_models.db_models import DatabaseDocument, DatabaseEmbeddingReference
from fastapi import HTTPException, UploadFile
from arthur_common.models.enums import DocumentType
from schemas.internal_schemas import Document
from sqlalchemy import or_
from sqlalchemy.orm import Session


class DocumentRepository:
    def __init__(self, db_session: Session, s3_client: MagicMock = S3Client):
        self.db_session = db_session
        self.s3_client = s3_client

    def create_document(self, file: UploadFile, user_id: str, is_global: bool):
        file_type = get_file_type(file.content_type)
        file_id = str(uuid.uuid4())
        file_path = self.s3_client.save_file(file_id, file)
        doc = DatabaseDocument(
            id=file_id,
            owner_id=user_id,
            is_global=is_global,
            type=file_type,
            name=file.filename,
            path=file_path,
        )
        self.db_session.add(doc)
        self.db_session.commit()
        return Document._from_database_model(doc)

    def get_documents(
        self,
        user_id: str = None,
    ):
        query = self.db_session.query(DatabaseDocument)

        if user_id is not None:
            query = query.filter(
                or_(
                    DatabaseDocument.owner_id == user_id,
                    DatabaseDocument.is_global.is_(True),
                ),
            )
        else:
            query = query.filter(DatabaseDocument.owner_id.is_(None))

        db_documents = query.all()
        documents = [Document._from_database_model(op) for op in db_documents]

        return documents

    def delete_document(self, document_id: str):
        doc = self.db_session.get(DatabaseDocument, document_id)
        if doc is None:
            raise HTTPException(
                status_code=404,
                detail="Document %s not found." % document_id,
            )
        for embedding in doc.embeddings:
            embedding_references = self.db_session.query(
                DatabaseEmbeddingReference,
            ).where(DatabaseEmbeddingReference.embedding_id == embedding.id)
            for reference in embedding_references:
                self.db_session.delete(reference)
        self.db_session.delete(doc)
        self.db_session.commit()
        return

    def get_file(self, document_id: str):
        doc = self.get_document_by_id(document_id)
        return self.s3_client.read_file(doc.path)

    def get_document_by_id(self, document_id: str):
        doc = self.db_session.get(DatabaseDocument, document_id)
        if doc is None:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found.",
            )
        return doc


def get_file_type(file_content_type: str):
    if file_content_type == "application/pdf":
        return DocumentType.PDF
    elif file_content_type == "text/csv":
        return DocumentType.CSV
    elif file_content_type == "text/plain":
        return DocumentType.TXT
    else:
        raise NotImplementedError
