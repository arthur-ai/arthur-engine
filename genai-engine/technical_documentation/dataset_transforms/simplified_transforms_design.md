# Simplified Dataset Transforms Design

## Overview

This document describes a simplified transform system for extracting data from OpenInference traces into datasets. The system uses **declarative JSON configurations** to define simple extraction rules that map trace span attributes to dataset columns.

**Key Characteristics:**
- **Dataset-level transforms**: Multiple reusable transforms per dataset
- **Simple filters**: Span name matching only (no complex relationships)
- **Frontend execution**: All transform logic runs in the browser
- **Manual review required**: All data additions require user review and confirmation
- **Declarative only**: No JavaScript code execution (Phase 1)

---

## 1. Transform Definition Schema

### JSON Structure

```json
{
  "version": "1.0",
  "columns": [
    {
      "column_name": "sqlQuery",
      "span_name": "rag-retrieval-savedQueries",
      "attribute_path": "attributes.input.value.sqlQuery",
      "fallback": null
    },
    {
      "column_name": "trace_id",
      "span_name": "llm: 'gpt-4.1'",
      "attribute_path": "traceId",
      "fallback": null
    }
  ]
}
```

### Field Definitions

- **`column_name`** (required): Target column in dataset
- **`span_name`** (required): Exact span name to match
- **`attribute_path`** (required): Dot-notation path to extract value (e.g., `"attributes.input.value.sqlQuery"`)
- **`fallback`** (optional): Default value if extraction fails (default: `null`)

### Execution Status Values

- **`success`**: Single value extracted successfully
- **`multiple_matches`**: Multiple spans matched, user selected one
- **`fallback`**: No match found, used fallback value
- **`manual`**: Manually entered value (no transform used)

---

## 2. Database Schema

### Table: `dataset_transforms`

```sql
CREATE TABLE dataset_transforms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    definition JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Multiple transforms per dataset, unique names
    UNIQUE(dataset_id, name)
);

CREATE INDEX idx_dataset_transforms_dataset_id 
    ON dataset_transforms(dataset_id);
```

### SQLAlchemy Model

Add to `src/db_models/dataset_models.py`:

```python
class DatabaseDatasetTransform(Base):
    __tablename__ = "dataset_transforms"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    definition: Mapped[dict] = mapped_column(postgresql.JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP, default=datetime.now())
    
    __table_args__ = (
        Index("idx_dataset_transforms_unique_name", "dataset_id", "name", unique=True),
    )


# Add relationship to existing DatabaseDataset model
class DatabaseDataset(Base):
    # ... existing fields ...
    transforms: Mapped[List["DatabaseDatasetTransform"]] = relationship(
        cascade="all, delete-orphan"
    )
```

### Metadata Storage in Rows

Add optional field to `dataset_version_rows.data` JSONB:

```json
{
  "columns": [
    {"column_name": "sqlQuery", "column_value": "SELECT * FROM users"}
  ],
  "metadata": {
    "trace_id": "trace-abc-123",
    "transform_id": "uuid-1",
    "added_at": "2025-11-15T12:00:00Z",
    "execution_result": "success"
  }
}
```

**Execution Result Values**:
- `success` - Single value extracted successfully
- `multiple_matches` - Multiple spans matched, user selected one
- `fallback` - No match found, used fallback value
- `manual` - Manually entered value (no transform used)

**Benefits of this metadata**:
- **Trace Provenance**: Link back to source trace for debugging and verification
- **Transform Tracking**: Know which transform was used (can look up name via ID)
- **Execution Status**: Know if there were multiple matches or fallbacks
- **Audit Trail**: Timestamp when data was added

---

## 3. API Endpoints

### Transform Management (CRUD)

```http
# List all transforms for a dataset
GET /api/v2/datasets/{dataset_id}/transforms

Response:
{
  "transforms": [
    {
      "id": "uuid-1",
      "dataset_id": "dataset-uuid",
      "name": "Extract SQL Queries",
      "description": "Extracts SQL queries and trace metadata",
      "definition": {
        "version": "1.0",
        "columns": [...]
      },
      "created_at": "2025-11-15T10:00:00Z",
      "updated_at": "2025-11-15T10:00:00Z"
    }
  ]
}

# Get specific transform
GET /api/v2/datasets/{dataset_id}/transforms/{transform_id}

Response:
{
  "id": "uuid-1",
  "dataset_id": "dataset-uuid",
  "name": "Extract SQL Queries",
  "description": "Optional description",
  "definition": {...},
  "created_at": "2025-11-15T10:00:00Z",
  "updated_at": "2025-11-15T10:00:00Z"
}

# Create transform
POST /api/v2/datasets/{dataset_id}/transforms
Content-Type: application/json

{
  "name": "Extract SQL Queries",
  "description": "Optional description",
  "definition": {
    "version": "1.0",
    "columns": [
      {
        "column_name": "sqlQuery",
        "span_name": "rag-retrieval-savedQueries",
        "attribute_path": "attributes.input.value.sqlQuery",
        "fallback": null
      }
    ]
  }
}

Response: 201 Created
{
  "id": "uuid-1",
  "dataset_id": "dataset-uuid",
  "name": "Extract SQL Queries",
  "definition": {...},
  "created_at": "2025-11-15T10:00:00Z"
}

# Update transform
PUT /api/v2/datasets/{dataset_id}/transforms/{transform_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "description": "Updated description",
  "definition": {...}
}

Response: 200 OK

# Delete transform
DELETE /api/v2/datasets/{dataset_id}/transforms/{transform_id}

Response: 204 No Content
```

### Add Data to Dataset

**Note**: Frontend executes transforms and sends extracted data.

```http
POST /api/v2/datasets/{dataset_id}/versions
Content-Type: application/json

{
  "rows_to_add": [
    {
      "data": [
        {
          "column_name": "sqlQuery",
          "column_value": "SELECT * FROM users"
        },
        {
          "column_name": "trace_id",
          "column_value": "trace-abc-123"
        }
      ],
      "metadata": {
        "trace_id": "trace-abc-123",
        "transform_id": "uuid-1",
        "added_at": "2025-11-15T12:00:00Z",
        "execution_result": "success"
      }
    }
  ]
}

Response: 200 OK
{
  "version_number": 2,
  "dataset_id": "dataset-uuid",
  "created_at": "2025-11-15T10:30:02Z",
  "rows": [...],
  "column_names": ["sqlQuery", "trace_id", "tokencount"],
  "total_count": 1
}
```

---

## 4. User Workflows

### Workflow 1: Create Transform

```
1. User navigates to Dataset Detail page
2. Clicks "Transforms" tab
3. Clicks "Create Transform" button
4. Fills in form:
   - Transform name
   - Description (optional)
   - Add columns:
     - Column name
     - Span name to match
     - Attribute path to extract
     - Fallback value
5. Can test transform on sample traces
6. Saves transform (POST to backend)
```

### Workflow 2: Add Trace to Dataset Using Transform

1. User views a trace and clicks "Add to Dataset"
2. Selects dataset and version from dropdowns
3. Selects transform from dropdown (or "Manual Entry")
4. Frontend executes transform and shows preview:
   - Table with columns: Column Name | Extracted Value | Status
   - If multiple spans match, user selects which one to use
   - User reviews extracted values
5. User clicks "Confirm" to add data
6. Frontend sends extracted data to backend with metadata:
   - `trace_id`, `transform_id`, `added_at`, `execution_result`

### Workflow 3: Manual Entry & Save as Transform

1. User follows steps 1-2 from Workflow 2
2. Selects "Manual Entry (No Transform)"
3. For each dataset column, user selects:
   - Span name from dropdown
   - Attribute path from dropdown
   - Value preview updates in real-time
4. User can either:
   - Click "Confirm" to add data without saving transform
   - Click "Save as Transform" to:
     - Enter transform name and description
     - Review generated JSON definition
     - Save transform and add data with transform metadata

---

## 5. Example Transform

**Extract SQL Queries from RAG Traces**:

```json
{
  "version": "1.0",
  "columns": [
    {
      "column_name": "sql_query",
      "span_name": "rag-retrieval-savedQueries",
      "attribute_path": "attributes.input.value.sqlQuery",
      "fallback": null
    },
    {
      "column_name": "result_count",
      "span_name": "rag-retrieval-savedQueries",
      "attribute_path": "attributes.output.resultCount",
      "fallback": 0
    }
  ]
}
```

---

