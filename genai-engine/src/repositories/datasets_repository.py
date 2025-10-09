import logging
from typing import List, Optional, Tuple
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from fastapi import HTTPException
from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import Session

from db_models import DatabaseDataset
from db_models.dataset_models import DatabaseDatasetVersion, DatabaseDatasetVersionRow
from schemas.internal_schemas import Dataset, DatasetVersion
from schemas.request_schemas import DatasetUpdateRequest, NewDatasetVersionRequest

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
        if update_dataset_request.name is not None:
            db_dataset.name = update_dataset_request.name
        if update_dataset_request.description is not None:
            db_dataset.description = update_dataset_request.description
        if update_dataset_request.metadata is not None:
            db_dataset.dataset_metadata = update_dataset_request.metadata

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

        # apply roting
        if pagination_params.sort == PaginationSortMethod.DESCENDING:
            base_query = base_query.order_by(desc(DatabaseDataset.created_at))
        elif pagination_params.sort == PaginationSortMethod.ASCENDING:
            base_query = base_query.order_by(asc(DatabaseDataset.created_at))

        # calculate total count before offset to apply pagination
        count = base_query.count()

        base_query = base_query.offset(
            pagination_params.page * pagination_params.page_size,
        )
        db_datasets = base_query.limit(pagination_params.page_size).all()

        return [
            Dataset._from_database_model(db_dataset) for db_dataset in db_datasets
        ], count

    def delete_dataset(self, dataset_id: UUID):
        # TODO: should we be archiving datasets? or is it fine to hard-delete?
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
            base_query = base_query.order_by(DatabaseDatasetVersionRow.id.asc())
        else:
            base_query = base_query.order_by(DatabaseDatasetVersionRow.id.desc())

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

    def create_dataset_version(
        self,
        dataset_id: UUID,
        dataset_version: NewDatasetVersionRequest,
    ) -> None:
        try:
            latest_version = self._get_latest_db_dataset_version(dataset_id)
        except HTTPException:
            # no version exists for this dataset yet
            latest_version = None

        dataset_version = DatasetVersion._from_request_model(
            dataset_id,
            latest_version,
            dataset_version,
        )
        self.db_session.add(dataset_version._to_database_model())
        self.db_session.commit()
