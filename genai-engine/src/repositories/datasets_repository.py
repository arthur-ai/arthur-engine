import logging
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from fastapi import HTTPException
from sqlalchemy import and_, asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db_models import DatabaseDataset
from db_models.dataset_models import (
    DatabaseDatasetTransform,
    DatabaseDatasetVersion,
    DatabaseDatasetVersionRow,
)
from schemas.internal_schemas import (
    Dataset,
    DatasetTransform,
    DatasetVersion,
    ListDatasetVersions,
)
from schemas.request_schemas import (
    DatasetTransformUpdateRequest,
    DatasetUpdateRequest,
    NewDatasetVersionRequest,
)

logger = logging.getLogger(__name__)


class DatasetRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_dataset(self, dataset: Dataset) -> None:
        db_dataset = dataset._to_database_model()
        self.db_session.add(db_dataset)
        self.db_session.commit()

    def _get_db_dataset(self, dataset_id: UUID) -> DatabaseDataset:
        db_dataset = (
            self.db_session.query(DatabaseDataset)
            .filter(DatabaseDataset.id == dataset_id)
            .first()
        )
        if not db_dataset:
            raise HTTPException(
                status_code=404,
                detail="Dataset %s not found." % dataset_id,
                headers={"full_stacktrace": "false"},
            )
        return db_dataset

    def get_dataset(self, dataset_id: UUID) -> Dataset:
        db_dataset = self._get_db_dataset(dataset_id)
        return Dataset._from_database_model(db_dataset)

    def update_dataset(
        self,
        dataset_id: UUID,
        update_dataset_request: DatasetUpdateRequest,
    ) -> None:
        db_dataset = self._get_db_dataset(dataset_id)
        if update_dataset_request.name:
            db_dataset.name = update_dataset_request.name
        if update_dataset_request.description is not None:
            db_dataset.description = update_dataset_request.description
        if update_dataset_request.metadata is not None:
            db_dataset.dataset_metadata = update_dataset_request.metadata

        db_dataset.updated_at = datetime.now()

        self.db_session.commit()

    def query_datasets(
        self,
        pagination_params: PaginationParameters,
        dataset_ids: Optional[list[UUID]] = None,
        dataset_name: Optional[str] = None,
    ) -> Tuple[List[Dataset], int]:
        base_query = self.db_session.query(DatabaseDataset)
        # apply filters
        if dataset_ids is not None:
            base_query = base_query.where(DatabaseDataset.id.in_(dataset_ids))
        if dataset_name:
            base_query = base_query.where(
                DatabaseDataset.name.ilike(f"%{dataset_name}%"),
            )

        # apply sorting - sort by updated_at field
        if pagination_params.sort == PaginationSortMethod.DESCENDING:
            base_query = base_query.order_by(desc(DatabaseDataset.updated_at))
        elif pagination_params.sort == PaginationSortMethod.ASCENDING:
            base_query = base_query.order_by(asc(DatabaseDataset.updated_at))

        # calculate total count before offset to apply pagination
        count = base_query.count()

        base_query = base_query.offset(
            pagination_params.page * pagination_params.page_size,
        )
        db_datasets = base_query.limit(pagination_params.page_size).all()

        return [
            Dataset._from_database_model(db_dataset) for db_dataset in db_datasets
        ], count

    def delete_dataset(self, dataset_id: UUID) -> None:
        db_dataset = self._get_db_dataset(dataset_id)
        self.db_session.delete(db_dataset)
        self.db_session.commit()

    def _get_latest_db_dataset_version(
        self,
        dataset_id: UUID,
    ) -> DatabaseDatasetVersion:
        db_dataset_version = (
            self.db_session.query(DatabaseDatasetVersion)
            .filter(DatabaseDatasetVersion.dataset_id == dataset_id)
            .order_by(DatabaseDatasetVersion.version_number.desc())
            .first()
        )
        if not db_dataset_version:
            raise HTTPException(
                status_code=404,
                detail="Dataset version for dataset %s not found." % dataset_id,
                headers={"full_stacktrace": "false"},
            )
        return db_dataset_version

    def get_latest_dataset_version(self, dataset_id: UUID) -> DatasetVersion:
        db_dataset_version = self._get_latest_db_dataset_version(dataset_id)
        # return page params representing that all rows have been fetched
        return DatasetVersion._from_database_model(
            db_dataset_version,
            len(db_dataset_version.version_rows),
            PaginationParameters(
                page=0,
                page_size=len(db_dataset_version.version_rows),
            ),
        )

    def get_dataset_version(
        self,
        dataset_id: UUID,
        dataset_version: int,
        pagination_params: PaginationParameters,
    ) -> DatasetVersion:
        base_query = (
            self.db_session.query(DatabaseDatasetVersion, DatabaseDatasetVersionRow)
            .join(
                DatabaseDatasetVersionRow,
                and_(
                    DatabaseDatasetVersionRow.version_number
                    == DatabaseDatasetVersion.version_number,
                    DatabaseDatasetVersionRow.dataset_id
                    == DatabaseDatasetVersion.dataset_id,
                ),
                isouter=True,
            )
            .filter(DatabaseDatasetVersion.dataset_id == dataset_id)
            .filter(DatabaseDatasetVersion.version_number == dataset_version)
        )

        # apply pagination
        total_count = base_query.count()

        if pagination_params.sort == PaginationSortMethod.ASCENDING:
            base_query = base_query.order_by(DatabaseDatasetVersionRow.created_at.asc())
        else:
            base_query = base_query.order_by(
                DatabaseDatasetVersionRow.created_at.desc(),
            )

        offset = pagination_params.page * pagination_params.page_size
        paginated_results = (
            base_query.offset(offset).limit(pagination_params.page_size).all()
        )

        if not paginated_results:
            raise HTTPException(
                status_code=404,
                detail="Dataset version for dataset %s not found." % dataset_id,
                headers={"full_stacktrace": "false"},
            )

        # every row will have the same version because of how the query was constructed, so we can just select
        # the first element of the first row as the dataset version
        db_dataset_version = paginated_results[0][0]

        # extract paginated rows from the version (in the second element for every row)
        # if the version has no rows, tuple will be [db_version, None]
        paginated_rows = [
            result[1] for result in paginated_results if result[1] is not None
        ]
        db_dataset_version.version_rows = paginated_rows
        return DatasetVersion._from_database_model(
            db_dataset_version,
            total_count,
            pagination_params,
        )

    def get_dataset_version_row(
        self,
        dataset_id: UUID,
        dataset_version: int,
        row_id: UUID,
    ) -> DatabaseDatasetVersionRow:
        """Get a specific row by ID from a dataset version"""
        db_row = (
            self.db_session.query(DatabaseDatasetVersionRow)
            .filter(
                DatabaseDatasetVersionRow.dataset_id == dataset_id,
                DatabaseDatasetVersionRow.version_number == dataset_version,
                DatabaseDatasetVersionRow.id == row_id,
            )
            .first()
        )

        if not db_row:
            raise HTTPException(
                status_code=404,
                detail=f"Row {row_id} not found in dataset {dataset_id} version {dataset_version}",
                headers={"full_stacktrace": "false"},
            )

        return db_row

    def create_dataset_version(
        self,
        dataset_id: UUID,
        dataset_version: NewDatasetVersionRequest,
    ) -> None:
        db_dataset = self._get_db_dataset(dataset_id)
        try:
            latest_version = self._get_latest_db_dataset_version(dataset_id)
        except HTTPException:
            # no version exists for this dataset yet
            latest_version = None

        internal_dataset_version = DatasetVersion._from_request_model(
            dataset_id,
            latest_version,
            dataset_version,
        )
        self.db_session.add(internal_dataset_version._to_database_model())
        db_dataset.updated_at = datetime.now()
        db_dataset.latest_version_number = internal_dataset_version.version_number
        self.db_session.commit()

    def get_dataset_versions(
        self,
        dataset_id: UUID,
        latest_version_only: bool,
        pagination_params: PaginationParameters,
    ) -> ListDatasetVersions:
        base_query = self.db_session.query(DatabaseDatasetVersion).filter(
            DatabaseDatasetVersion.dataset_id == dataset_id,
        )

        # get total count before applying additional filters
        total_count = base_query.count()

        # get first dataset in descending order if latest_version_only filter is set
        applied_page_params = (
            PaginationParameters(
                sort=PaginationSortMethod.DESCENDING,
                page_size=1,
                page=0,
            )
            if latest_version_only
            else pagination_params
        )

        total_count = 1 if latest_version_only and total_count != 0 else total_count

        # apply pagination
        if applied_page_params.sort == PaginationSortMethod.ASCENDING:
            base_query = base_query.order_by(
                DatabaseDatasetVersion.version_number.asc(),
            )
        else:
            base_query = base_query.order_by(
                DatabaseDatasetVersion.version_number.desc(),
            )

        offset = applied_page_params.page * applied_page_params.page_size
        dataset_versions = (
            base_query.offset(offset).limit(applied_page_params.page_size).all()
        )

        return ListDatasetVersions._from_database_model(
            dataset_versions,
            total_count,
            pagination_params,
        )

    # Transform methods
    def create_transform(self, transform: DatasetTransform) -> None:
        # Verify dataset exists
        self._get_db_dataset(transform.dataset_id)
        db_transform = transform._to_database_model()
        self.db_session.add(db_transform)
        try:
            self.db_session.commit()
        except IntegrityError as e:
            self.db_session.rollback()
            # Check if it's a unique constraint violation
            if (
                "UNIQUE constraint failed" in str(e)
                or "duplicate key" in str(e).lower()
            ):
                raise HTTPException(
                    status_code=409,
                    detail=f"A transform with name '{transform.name}' already exists for this dataset.",
                    headers={"full_stacktrace": "false"},
                )
            # Re-raise if it's a different integrity error
            raise HTTPException(
                status_code=400,
                detail="Database constraint violation.",
                headers={"full_stacktrace": "false"},
            )

    def _get_db_transform(
        self,
        dataset_id: UUID,
        transform_id: UUID,
    ) -> Optional[DatabaseDatasetTransform]:
        return (
            self.db_session.query(DatabaseDatasetTransform)
            .filter(DatabaseDatasetTransform.dataset_id == dataset_id)
            .filter(DatabaseDatasetTransform.id == transform_id)
            .first()
        )

    def get_transform(self, dataset_id: UUID, transform_id: UUID) -> DatasetTransform:
        db_transform = self._get_db_transform(dataset_id, transform_id)
        if not db_transform:
            raise HTTPException(
                status_code=404,
                detail="Transform %s not found for dataset %s."
                % (transform_id, dataset_id),
                headers={"full_stacktrace": "false"},
            )
        return DatasetTransform._from_database_model(db_transform)

    def list_transforms(self, dataset_id: UUID) -> List[DatasetTransform]:
        # Verify dataset exists
        self._get_db_dataset(dataset_id)
        db_transforms = (
            self.db_session.query(DatabaseDatasetTransform)
            .filter(DatabaseDatasetTransform.dataset_id == dataset_id)
            .order_by(DatabaseDatasetTransform.created_at.desc())
            .all()
        )
        return [
            DatasetTransform._from_database_model(db_transform)
            for db_transform in db_transforms
        ]

    def update_transform(
        self,
        dataset_id: UUID,
        transform_id: UUID,
        update_request: DatasetTransformUpdateRequest,
    ) -> None:
        db_transform = self._get_db_transform(dataset_id, transform_id)
        if not db_transform:
            raise HTTPException(
                status_code=404,
                detail="Transform %s not found for dataset %s."
                % (transform_id, dataset_id),
                headers={"full_stacktrace": "false"},
            )

        if update_request.name is not None:
            db_transform.name = update_request.name
        if update_request.description is not None:
            db_transform.description = update_request.description
        if update_request.definition is not None:
            db_transform.definition = update_request.definition

        db_transform.updated_at = datetime.now()
        try:
            self.db_session.commit()
        except IntegrityError as e:
            self.db_session.rollback()
            # Check if it's a unique constraint violation
            if (
                "UNIQUE constraint failed" in str(e)
                or "duplicate key" in str(e).lower()
            ):
                raise HTTPException(
                    status_code=409,
                    detail=f"A transform with name '{update_request.name}' already exists for this dataset.",
                    headers={"full_stacktrace": "false"},
                )
            # Re-raise if it's a different integrity error
            raise HTTPException(
                status_code=400,
                detail="Database constraint violation.",
                headers={"full_stacktrace": "false"},
            )

    def delete_transform(self, dataset_id: UUID, transform_id: UUID) -> None:
        db_transform = self._get_db_transform(dataset_id, transform_id)
        if not db_transform:
            raise HTTPException(
                status_code=404,
                detail="Transform %s not found for dataset %s."
                % (transform_id, dataset_id),
                headers={"full_stacktrace": "false"},
            )
        self.db_session.delete(db_transform)
        self.db_session.commit()
