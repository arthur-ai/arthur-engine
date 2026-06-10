# GCS Image-URI Resolution — Technical Design Document

## Goal

Support image columns whose cell values are GCS bucket URIs (`gs://bucket/path/image.png`) in addition to inline base64. When the raw-data (FetchData) job runs in the engine, resolve each `gs://` value to a base64 string so the platform renders the image. Inline base64 continues to work unchanged.

## Plan

### Step 1: Create the `ImageResolver`

**Create File**: `ml-engine/src/ml_engine/tools/image_resolver.py`

`resolve_images` takes the rows and the dataset schema. It finds the image columns from the schema, and for each row it checks those columns for a `gs://` value. Anything that isn't a `gs://` string (inline base64, null) is left alone. For each `gs://` value it finds all the GCS connectors pointing at that bucket, attempts to read the image through all those connectors (first wins), and replaces the cell with the base64-encoded contents. Reads run in parallel. If an image can't be read, that cell is left as-is and the rest of the job continues.

```python
MAX_IMAGE_RESOLVER_WORKERS = 50 # same num as in BucketBasedConnector

class ImageResolver:
    def __init__(
        self,
        connector_constructor: ConnectorConstructor,
        project_id: str,
        logger: Logger,
    ) -> None:
        self.connector_constructor = connector_constructor
        self.project_id = project_id
        self.logger = logger
        self._connectors_for_type: dict[ConnectorType, list[ConnectorSpec]] = {}
        self._connectors_for_bucket: dict[str, list[ConnectorSpec]] = {}

    def resolve_images(
        self,
        rows: list[dict[str, Any]],
        schema: DatasetSchema,
    ) -> list[dict[str, Any]]:
        image_cols = self._get_image_columns(schema)
        if not image_cols:
            return rows

        with ThreadPoolExecutor(max_workers=MAX_IMAGE_RESOLVER_WORKERS) as executor:
            future_to_cell = {}
            for i, row in enumerate(rows):
                for col in image_cols:
                    value = row.get(col)
                    
                    if not (isinstance(value, str) and is_supported_image_uri(value)):
                        continue

                    future = executor.submit(self._extract_image, value)
                    future_to_cell[future] = (i, col)

            for future in as_completed(future_to_cell):
                row, col = future_to_cell[future]
                try:
                    rows[row][col] = future.result()
                except Exception as e:
                    self.logger.info(
                        f"Image resolve failed for row {row} col {col}: {e}"
                    )

        return rows

    @staticmethod
    def _get_image_columns(schema: DatasetSchema) -> list[str]:
        image_columns = []
        for col in schema.columns:
            if isinstance(col.definition, DatasetScalarType) and col.definition.dtype == DType.IMAGE:
                image_columns.append(schema.column_names[col.id])

        return image_columns

    def _extract_image(self, image_uri: str) -> str:
        matches = self._get_connectors_for_image(image_uri)
        if len(matches) > 1:
            self.logger.warning(
                f"Ambiguous image_uri {image_uri} matched {len(matches)} connectors"
            )
        elif len(matches) == 0:
            self.logger.error(
                f"No connectors found for image {image_uri}"
            )
            return image_uri

        for connector in matches:
            try:
                return connector.extract_image(image_uri)
            except Exception as e:
                continue

        self.logger.error(f"Could not read image {image_uri}")
        return image_uri  # All failed

    def _get_connectors_for_image(self, image_uri: str) -> list[ConnectorSpec]:
        connector_type = get_connector_type_for_image_uri(image_uri)
        if not connector_type:
            return []

        bucket = get_bucket_from_uri(image_uri)
        if not bucket:
            return []

        if bucket in self._connectors_for_bucket:
            return self._connectors_for_bucket[bucket]

        if connector_type not in self._connectors_for_type:
            self._connectors_for_type[connector_type] = self.connector_constructor.get_connectors_for_type(
                self.project_id,
                connector_type,
            )
        
        connectors_for_bucket = []
        for connector in self._connectors_for_type[connector_type]:
            for f in connector.fields:
                if f.key == BUCKET_BASED_CONNECTOR_BUCKET_FIELD and f.value == bucket:
                    connectors_for_bucket.append(connector)
        
        self._connectors_for_bucket[bucket] = connectors_for_bucket
        return connectors_for_bucket
```

### Step 1B: Add helper functions for supported images and connectors

**Add File**: `ml-engine/src/ml_engine/tools/image_connector_tools.py`

```python
IMAGE_CONNECTOR_PREFIX_TO_TYPE = {
    "gs://": ConnectorType.GCS
}
IMAGE_CONNECTOR_PREFIX_TUPLE = tuple(IMAGE_CONNECTOR_PREFIX_TO_TYPE.keys())

def is_supported_image_uri(uri: str):
    return uri.startswith(IMAGE_CONNECTOR_PREFIX_TUPLE)

def get_connector_type_for_image_uri(image_uri: str):
    for key, val in IMAGE_CONNECTOR_PREFIX_TO_TYPE.items():
        if image_uri.startswith(key):
            return val
    
    return None

def get_bucket_from_uri(image_uri: str):
    _, _, rest = image_uri.partition("://")
    if not rest:
        return None
    
    bucket, _, _ = rest.partition("/")
    if not bucket:
        return None

    return bucket
```

### Step 2: Add `get_connectors_for_type` to `ConnectorConstructor`

**Edit File**: `ml-engine/src/ml_engine/tools/connector_constructor.py`

```python
def get_connectors_for_type(
    self, project_id: str, connector_type: ConnectorType
) -> list[ConnectorSpec]:
    return self.connectors_client.get_connectors(
        project_id=project_id,
        connector_type=connector_type,
        page_size=1000,
    ).records
```

### Step 2B: Add `extract_image` to connector base class and bucket-based connectors

**Edit File**: `ml-engine/src/ml_engine/connectors/connector.py`

Default returns the URI unchanged, so connectors that can't extract images leave the cell as-is:

```python
def extract_image(self, image_uri: str) -> str:
    return image_uri
```

**Edit File**: `ml-engine/src/ml_engine/connectors/bucket_based_connector.py`

Override bucket-based connectors:

```python
def extract_image(self, image_uri: str) -> str:
    blob = self.file_system.cat(image_uri)
    return base64.b64encode(blob).decode("ascii")
```

### Step 3: Call the resolver in `FetchDataExecutor`

**Edit File**: `ml-engine/src/ml_engine/job_executors/fetch_data_executor.py`
Replace the `if hasattr(job_spec, "operation_id")` block in `execute()` (lines 106-112):

```python
    if hasattr(job_spec, "operation_id"):
        dataset = get_dataset_or_available_dataset_from_id(datasets_client, dataset_id) # new helper
        if dataset.dataset_schema:
            schema = client_to_common_dataset_schema(dataset.dataset_schema)
            image_resolver = ImageResolver(
                self.connector_constructor,
                dataset.project_id,
                self.logger,
            )
            
            data = image_resolver.resolve_images(data, schema)

        self._store_data(
            job_spec.dataset_id,
            job_spec.available_dataset_id,
            job_spec.operation_id,
            data,
        )
```

extract `_dataset_or_available_dataset_from_id` into a common helper called `get_dataset_or_available_dataset_from_id`