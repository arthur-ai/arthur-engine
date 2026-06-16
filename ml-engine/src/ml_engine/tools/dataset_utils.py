from arthur_client.api_bindings import AvailableDataset, Dataset, DatasetsV1Api
from arthur_client.api_bindings.exceptions import NotFoundException


def get_dataset_or_available_dataset_from_id(
    datasets_client: DatasetsV1Api,
    dataset_id: str,
) -> Dataset | AvailableDataset:
    try:
        return datasets_client.get_dataset(dataset_id)
    except NotFoundException:
        return datasets_client.get_available_dataset(dataset_id)
