# Proposal: Semi-Automated Trace-to-Dataset Transform System

## 1. Context

We're building a system that lets users extract structured information from **OpenInference traces** into **datasets**. Each dataset has columns, and each column can have user-defined transform functions that describe how to find or derive a value from a trace or its spans.

**Current State**: Users manually select spans via dropdown navigation, select nested keys from span JSON, and optionally edit values before saving.

**Goal**: Enable two complementary workflows:

1. **Automatic Addition**: User clicks a button, transforms execute, data saves to database with no manual intervention. Ideal for bulk operations.

2. **Manual Addition**: User clicks a button, sees results from existing transforms (read-only) and uses dropdowns to fill columns without transforms. Primary purpose is to create new transforms by saving dropdown selections as reusable transforms for that column.

**Architecture**: All transforms execute on the **frontend** for instant preview, reduced backend complexity, and consistent behavior between testing and production.


---

## 2. Data Model

Each trace (`TraceResponse`) contains:

* `trace_id`, start/end times, etc.
* `root_spans`: list of root `NestedSpanWithMetricsResponse` objects.

Each span (`NestedSpanWithMetricsResponse`) contains:

* `span_id`, `span_name`, `status_code`, etc.
* `span_kind`: OpenInference span kind (e.g., `LLM`, `RETRIEVER`, `AGENT`, `TOOL`, `CHAIN`, `EMBEDDING`)
* `raw_data` — Full OpenTelemetry span data following OpenInference semantic conventions:
  - **Attributes**: Standard OpenInference attributes like:
    - `llm.model_name`, `llm.input_messages`, `llm.output_messages`
    - `llm.token_count.prompt`, `llm.token_count.completion`
    - `retrieval.documents`, `tool.name`, `tool.parameters`
    - etc.
* Computed fields like `input_content` and `output_content` (derived from OpenInference attributes).
* Recursive `children` spans (forming a tree).

**Reference**: [OpenInference Semantic Conventions](https://github.com/Arize-ai/openinference)

---

## 3. Transform Types

### **1. Declarative JSON/YAML Configuration (Phase 1 - MVP)**

Rule-based configuration for tree navigation and filtering. Users specify filters and extraction paths without writing code.

**Format Options**:
- **JSON**: Explicit, matches storage format, better for programmatic generation
- **YAML**: Concise, human-friendly, less syntax noise

Both formats are equivalent and interconvertible.

#### Filter Schema

The declarative filter supports flexible tree navigation with the following filter operators:

**Basic Filters:**
- `span_kind`: Match span kind (e.g., "LLM", "TOOL", "AGENT", "RETRIEVER", "CHAIN", "EMBEDDING")
- `span_name`: Match span name (exact string or regex pattern)
- `status_code`: Match status code (e.g., "OK", "ERROR")
- `attributes`: Match OpenInference attributes (nested path matching)

**Relationship Filters:**
- `has_child`: Check if span has a child matching nested filter criteria
- `has_parent`: Check if span has a parent matching nested filter criteria
- `has_descendant`: Check if span has any descendant matching nested filter criteria
- `has_ancestor`: Check if span has any ancestor matching nested filter criteria

**Logical Operators:**
- `AND`: All conditions must match (default when multiple filters specified)
- `OR`: Any condition must match
- `NOT`: Negate a condition

**Attribute Matching:**
- `attributes.<path>`: Match nested attribute path (e.g., `attributes.llm.model_name`)
- Supports exact match, regex patterns, and nested object matching

#### Examples

**Example 1: Basic filter - LLM span with TOOL child**

```json
{
  "version": "1.0",
  "filter": {
    "span_kind": "LLM",
    "has_child": {
      "span_kind": "TOOL"
    }
  },
  "return": {
    "path": "input_content",
    "fallback": null
  }
}
```

**Example 2: Child with specific name**

```json
{
  "version": "1.0",
  "filter": {
    "span_kind": "LLM",
    "has_child": {
      "span_kind": "TOOL",
      "span_name": "weather_api"
    }
  },
  "return": {
    "path": "input_content",
    "fallback": null
  }
}
```

**Example 3: Parent-based filtering - LLM span if parent is Agent**

```json
{
  "version": "1.0",
  "filter": {
    "span_kind": "LLM",
    "has_parent": {
      "span_kind": "AGENT"
    }
  },
  "return": {
    "path": "output_content",
    "fallback": null
  }
}
```

**Example 4: Complex nested conditions - Agent span with LLM child that has TOOL descendant**

```json
{
  "version": "1.0",
  "filter": {
    "span_kind": "AGENT",
    "has_child": {
      "span_kind": "LLM",
      "has_descendant": {
        "span_kind": "TOOL",
        "span_name": "search_tool"
      }
    }
  },
  "return": {
    "path": "input_content",
    "fallback": null
  }
}
```

**Example 5: Attribute-based filtering**

```json
{
  "version": "1.0",
  "filter": {
    "span_kind": "LLM",
    "attributes.llm.model_name": "gpt-4",
    "has_child": {
      "span_kind": "TOOL"
    }
  },
  "return": {
    "path": "raw_data.attributes.llm.token_count.prompt",
    "fallback": 0
  }
}
```

**Example 6: Regex pattern matching**

```json
{
  "version": "1.0",
  "filter": {
    "span_kind": "TOOL",
    "span_name": {
      "$regex": "^api_"
    }
  },
  "return": {
    "path": "raw_data.attributes.tool.parameters",
    "fallback": null
  }
}
```

**Example 7: OR condition - Multiple span kinds**

```json
{
  "version": "1.0",
  "filter": {
    "$or": [
      { "span_kind": "LLM" },
      { "span_kind": "EMBEDDING" }
    ],
    "has_parent": {
      "span_kind": "CHAIN"
    }
  },
  "return": {
    "path": "input_content",
    "fallback": null
  }
}
```

**YAML Format Example:**

```yaml
# Equivalent to JSON Example 2
version: "1.0"
filter:
  span_kind: "LLM"
  has_child:
    span_kind: "TOOL"
    span_name: "weather_api"
return:
  path: "input_content"
  fallback: null
```

**Execution**: Frontend JavaScript traversal engine parses and applies config recursively. Supports child/parent/descendant/ancestor relationships, attribute matching, regex patterns, and logical operators (AND/OR/NOT).

**Benefits**: Safe (no code execution), easy to serialize, UI-friendly, instant preview, schema-validated.

**Limitations**: Limited expressiveness for complex logic or computations. Use JavaScript transforms for advanced cases.

---

### **2. JavaScript Transform Functions (Phase 2 - Power Users)**

Programmatic transforms for complex extraction logic. Users write JavaScript functions executed in a sandboxed browser environment.

**Example**:

```javascript
/**
 * Extract input content from LLM spans that have a TOOL child
 * @param {TraceResponse} trace - Full OpenInference trace object with nested spans
 * @returns {string|null} Extracted value or null
 */
function extractValue(trace) {
  // Helper functions provided by framework
  for (const rootSpan of trace.root_spans) {
    // Find LLM span using OpenInference span_kind
    const llmSpan = findSpanRecursive(
      rootSpan, 
      span => span.span_kind === "LLM"
    );
    
    // Check if LLM span has a TOOL child
    if (llmSpan && hasChildOfKind(llmSpan, "TOOL")) {
      // Return computed field (derived from OpenInference llm.input_messages)
      return llmSpan.input_content;
    }
  }
  
  return null;
}
```

**Execution Environment**: Sandboxed `<iframe>` with CSP restrictions. No network, storage, or DOM access. 5-second timeout.

**Helper Functions**:

```javascript
// Find span recursively by predicate
findSpanRecursive(span, predicate) → Span | null

// Check if span has child of specific OpenInference span kind
hasChildOfKind(span, spanKind) → boolean

// Check if span has parent of specific OpenInference span kind
hasParentOfKind(span, spanKind) → boolean

// Extract nested value from object by path
extractNestedPath(obj, path) → any

// Get all descendants of a span
getDescendants(span) → Span[]

// Filter spans by condition
filterSpans(spans, predicate) → Span[]

// Get OpenInference attribute value
getOpenInferenceAttribute(span, attributeName) → any
```

**Benefits**: Instant execution, full programmatic control, no backend load, Monaco Editor integration, TypeScript definitions.

---

## 4. Lifecycle & Architecture

### Core Concept

Transforms follow a **two-tier architecture**:
1. **Transform Definitions** (dataset-scoped): Reusable extraction logic
2. **Column Mappings** (version-scoped): Apply transforms to specific columns in specific versions

This separation enables:
- **Reusability**: One transform used across multiple versions/columns
- **Versioning**: Different dataset versions can use different transforms for same column
- **Flexibility**: Activate/deactivate transforms without deletion

---

### Lifecycle Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. DEFINE TRANSFORM (dataset-scoped)                            │
│    User creates transform in Transforms tab                     │
│    → Stored in transform_definitions table                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. MAP TO COLUMNS (version-scoped)                              │
│    User maps transform to column(s) in specific version         │
│    → Stored in transform_column_mappings table                  │
│    → One transform per column (overwrite to change)             │
└─────────────────────────────────────────────────────────────────┘
                              
                        ┌─────┴──────────────────────────────────────┐
                        ↓                                            ↓
        ┌───────────────────────────────────────┐  ┌───────────────────────────────────────┐
        │ 3A. AUTOMATIC ADD TO DATASET          │  │ 3B. MANUAL ADD TO DATASET             │
        │                                       │  │                                       │
        │ Button: "Add to Dataset (Automatic)"  │  │ Button: "Add to Dataset (Manual)"     │
        │                                       │  │                                       │
        │ → Execute transforms                  │  │ → Execute transforms (read-only)      │
        │ → Save directly to database           │  │ → Show dropdown for missing columns   │
        │ → No user intervention                │  │ → User reviews before saving          │
        │                                       │  │                                       │
        │                                       │  │ Optional: "Save as Transform"         │
        │                                       │  │ → Create + map transform from UI      │
        └───────────────────────────────────────┘  └───────────────────────────────────────┘
```

---

### State Machine

**Transform Definition States:**
- `draft`: Being authored/tested
- `active`: Available for use
- `inactive`: No longer in use

---

### Transform Versioning

- Edits to active transforms create new versions (immutable history)
- Column mappings can be upgraded to newer transform versions
- Maintains reproducibility for historical dataset rows

---

### UI Integration Points

**1. Define Transforms** (Dataset-Level)
- Location: Dataset detail page → "Transforms" tab
- Editor modes: Visual Builder, JSON/YAML Editor, JavaScript Editor (Phase 2)
- Actions: Test on sample traces, save to `transform_definitions`

**2. Map Transforms to Columns** (Version-Level)
- Location: Dataset version view → "Configure Transforms"
- Interface: Select transform per column (dropdown), toggle active/inactive
- Stored in: `transform_column_mappings`

**3. Add Trace to Dataset**
- Location: Trace detail page or traces list view
- **Automatic Button**: Execute transforms → save directly (no preview/edit)
- **Manual Button**: Execute transforms → show preview → allow edits/new transforms → save

---

## 5. Database Schema

**Table: `transform_definitions`**

| Column        | Type                             | Description                                    |
| ------------- | -------------------------------- | ---------------------------------------------- |
| `id`          | UUID                             | Transform definition ID                        |
| `dataset_id`  | UUID (FK to datasets)            | Dataset this transform belongs to              |
| `name`        | TEXT                             | Human-friendly name (e.g., "Extract LLM Input")|
| `description` | TEXT                             | Optional description of what it extracts       |
| `type`        | ENUM(`declarative`, `javascript`) | Transform type: declarative (JSON/YAML) or JavaScript |
| `definition`  | JSONB                            | Transform logic (schema-validated)             |
| `created_at`  | TIMESTAMP                        | Timestamp                                      |
| `updated_at`  | TIMESTAMP                        | Last update timestamp                          |

**Table: `transform_column_mappings`**

| Column              | Type                                  | Description                                  |
| ------------------- | ------------------------------------- | -------------------------------------------- |
| `id`                | UUID                                  | Mapping ID                                   |
| `transform_id`      | UUID (FK to transform_definitions)    | Which transform to apply                     |
| `dataset_id`        | UUID                                  | Dataset ID (for composite FK)                |
| `version_number`    | INTEGER                               | Dataset version (for composite FK)           |
| `column_name`       | TEXT                                  | Target column in this version                |
| `is_active`         | BOOLEAN                               | Whether this mapping is currently active     |
| `created_at`        | TIMESTAMP                             | When mapping was created                     |

**Foreign Key Constraints:**
- `(dataset_id, version_number)` → `dataset_versions(dataset_id, version_number)`
- `transform_id` → `transform_definitions(id)` with ON DELETE CASCADE
- `dataset_id` → `datasets(id)` with ON DELETE CASCADE

**Unique Constraint:**
- `UNIQUE(dataset_id, version_number, column_name)` - Each column can have only ONE active transform

**Index:**
- Composite index on `(dataset_id, version_number)` for fast version lookups

### Possible Enhancement

**Table: `dataset_version_rows`**

Add a metadata field to existing table:
* `transform_metadata` (JSONB): Records which transform populated each column

**Structure**:
```json
{
  "column_name": {
    "transform_id": "uuid",
    "transform_name": "Extract User Input",
    "executed_at": "2025-11-07T10:30:00Z",
    "execution_result": "success",  // or "fallback" or "error"
    "source": "automatic"  // "automatic" | "manual"
  }
}
```

**Source Values**:
- `automatic`: Added via "Add to Dataset (Automatic)" button
- `manual`: Added via "Add to Dataset (Manual)" button, user reviewed data before saving

---

## 6. Workflows

### Automatic Addition

**Trigger**: "Add to Dataset (Automatic)" button

**Flow**:
1. Frontend fetches active column mappings for the dataset version
2. Frontend executes transforms on trace(s) (client-side)
3. Frontend sends extracted data to backend API endpoint `POST /api/v2/datasets/{dataset_id}/versions` with `rows_to_add`
4. Backend creates new dataset version and stores rows with transform metadata (`source: "automatic"`)

**Use Case**: trusted transforms, quick-add

---

### Manual Addition

**Trigger**: "Add to Dataset (Manual)" button

**Flow**:
1. Frontend fetches active column mappings for the dataset version
2. Frontend executes available transforms on trace (client-side)
3. Opens modal showing:
   - Columns with transforms: Display extracted value (editable)
   - Columns without transforms: Show dropdown to select span/attribute path
4. User can click "Save as Transform" to convert dropdown selection into reusable transform
5. User reviews/edits values and saves to dataset via `POST /api/v2/datasets/{dataset_id}/versions` endpoint with `rows_to_add` and metadata (`source: "manual"`)

**Use Case**: First-time dataset population, creating new transforms, quality review

---

## 7. API Examples

### Create Declarative Transform

The API accepts the transform definition as JSON (which is also the storage format). See Section 3 for comprehensive examples of declarative transform definitions.

```http
POST /api/v2/datasets/{dataset_id}/transforms
Content-Type: application/json

{
  "name": "Extract User Input from LLM with Tool",
  "description": "Extracts input content from LLM spans that have a TOOL child",
  "type": "declarative",
  "definition": {
    "version": "1.0",
    "filter": {
      "span_kind": "LLM",
      "has_child": {
        "span_kind": "TOOL"
      }
    },
    "return": {
      "path": "input_content",
      "fallback": null
    }
  }
}
```


### Create JavaScript Transform

```http
POST /api/v2/datasets/{dataset_id}/transforms
Content-Type: application/json

{
  "name": "Extract Model Name from LLM Spans",
  "description": "Extracts llm.model_name from LLM spans",
  "type": "javascript",
  "definition": {
    "version": "1.0",
    "function_body": "function extractValue(trace) {\n  for (const rootSpan of trace.root_spans) {\n    const llmSpan = findSpanRecursive(rootSpan, s => s.span_kind === 'LLM');\n    if (llmSpan) {\n      return getOpenInferenceAttribute(llmSpan, 'llm.model_name');\n    }\n  }\n  return null;\n}",
    "timeout_ms": 5000
  }
}
```

---

### Map Transform to Column

```http
POST /api/v2/datasets/{dataset_id}/versions/{version_number}/column-mappings
Content-Type: application/json

{
  "transform_id": "abc-123",
  "column_name": "user_input",
  "is_active": true
}
```

---

### Add Traces to Dataset (Both Automatic and Manual Workflows)

**Endpoint**: Both workflows use the same endpoint to create a new dataset version with added rows. Frontend executes transforms before calling this endpoint.

**Note**: See "Workflows" section (Section 6) for detailed flow descriptions. The difference between automatic and manual workflows is only in the `source` field within `transform_metadata` (`"automatic"` vs `"manual"`).

```http
POST /api/v2/datasets/{dataset_id}/versions
Content-Type: application/json

{
  "rows_to_add": [
    {
      "data": [
        {
          "column_name": "user_input",
          "column_value": "What is the weather today?"
        },
        {
          "column_name": "model_name",
          "column_value": "gpt-4"
        }
      ],
      "transform_metadata": {
        "user_input": {
          "transform_id": "abc-123",
          "transform_name": "Extract User Input from LLM with Tool",
          "executed_at": "2025-11-06T10:30:00Z",
          "execution_result": "success",
          "source": "automatic"
        },
        "model_name": {
          "transform_id": "def-456",
          "transform_name": "Extract Model Name",
          "executed_at": "2025-11-06T10:30:00Z",
          "execution_result": "success",
          "source": "automatic"
        }
      }
    }
  ],
  "rows_to_delete": [],
  "rows_to_update": []
}

Response:
{
  "version_number": 2,
  "dataset_id": "dataset-uuid",
  "created_at": "2025-11-06T10:30:02Z",
  "rows": [
    {
      "id": "row-uuid-1",
      "data": [
        {
          "column_name": "user_input",
          "column_value": "What is the weather today?"
        },
        {
          "column_name": "model_name",
          "column_value": "gpt-4"
        }
      ],
      "created_at": "2025-11-06T10:30:02Z"
    }
  ],
  "column_names": ["user_input", "model_name"],
  "total_count": 1
}
```

**Note**: The `transform_metadata` field is stored in the `dataset_version_rows` table (see Section 5). For manual workflow, use `source: "manual"` instead of `"automatic"`.

---

### Preview for Manual Addition

**Optional Endpoint**: Returns column mappings for preview. Frontend executes transforms locally.

**Note**: Frontend can also fetch column mappings via GET endpoint and execute transforms directly on trace data it already has.

```http
GET /api/v2/datasets/{dataset_id}/versions/{version_number}/column-mappings

Response:
{
  "column_mappings": [
    {
      "column_name": "user_input",
      "transform_id": "abc-123",
      "transform_name": "Extract User Input",
      "transform_definition": {
        "version": "1.0",
        "filter": { ... },
        "return": { ... }
      },
      "is_active": true
    },
    {
      "column_name": "response",
      "transform_id": null,
      "is_active": false
    }
  ]
}
```

**Frontend then**: Executes transforms on trace data, shows preview with extracted values.

---

### Save Transform from Manual Selection

**Endpoint**: Creates transform definition from dropdown selections and maps to column

```http
POST /api/v2/datasets/{dataset_id}/versions/{version_number}/transforms/from-selection
Content-Type: application/json

{
  "column_name": "user_input",
  "transform_name": "Extract User Query from Tool Call",
  "transform_description": "Gets input from LLM spans that have a TOOL child",
  "selections": {
    "span_kind": "LLM",
    "has_child": {
      "span_kind": "TOOL"
    },
    "return_path": "input_content"
  }
}

Response:
{
  "transform_id": "new-transform-uuid",
  "transform_name": "Extract User Query from Tool Call",
  "column_mapping_created": true,
  "definition": {
    "version": "1.0",
    "filter": {
      "span_kind": "LLM",
      "has_child": {
        "span_kind": "TOOL"
      }
    },
    "return": {
      "path": "input_content",
      "fallback": null
    }
  }
}
```

**Note**: The `selections` object supports the same filter patterns as declarative transforms (see Section 3), including nested relationships like `has_child`, `has_parent`, `has_descendant`, `has_ancestor`, and span name matching.

---

## 8. Key Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| **1. How will transforms be created?** | Visual builder + JSON/YAML editor (Phase 1), JavaScript code editor (Phase 2) | Balance ease-of-use for non-technical users with power for developers |
| **2. Transform types supported?** | Declarative (JSON/YAML) and JavaScript | Declarative for common patterns, JavaScript for complex logic |
| **3. Execution location?** | Frontend (browser) for all transforms | Instant preview, reduced backend load, consistent testing and production behavior |
| **4. Dataset or version association?** | Both: definitions at dataset level, column mappings at version level | Enables reusability while maintaining version isolation |
| **5. Storage structure?** | Two tables: `transform_definitions` + `transform_column_mappings` | Separates transform logic from version-specific application |
| **6. Add to dataset workflows?** | Two buttons: "Add to Dataset (Automatic)" for direct save, "Add to Dataset (Manual)" for review/edit | Automatic for bulk operations, manual for review and transform creation |
| **7. Transform versioning?** | Immutable with parent_id lineage | Preserves reproducibility while allowing evolution |


## JS In-depth Implementation Strategy

### Use a sandboxed iframe

- Create a hidden <iframe sandbox="allow-scripts">.
- Inject minimal HTML + a script that:
    - Listens for messages (window.onmessage).
    - Executes user code safely via new Function("data", "helpers", code).
    - Captures console.log calls and sends logs/results back to parent with postMessage.
- No access to window, document, or external APIs.

### Validate code before running

```
const forbidden = /\b(window|document|fetch|XMLHttpRequest|localStorage|navigator|location|importScripts)\b/;
if (forbidden.test(code)) throw new Error("Disallowed API usage");
```

### Add timeout protection

Set a 2-3s timeout in the parent.
If no message is received → reload the iframe to kill execution.

### Capture logs and results

- The iframe intercepts console.log and sends them to the parent.
- The parent component stores them in React state and displays them for debugging.

## Example Components

FormulaSandbox.tsx
```
import React, { useRef, useEffect, useState } from "react";

const FormulaSandbox: React.FC = () => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [code, setCode] = useState('// Example\nreturn helpers.avg(data.values);');
  const [logs, setLogs] = useState<string[]>([]);
  const [result, setResult] = useState<string>("");

  const data = { values: [10, 20, 30, 40] };
  const helpers = {
    sum: (a: number[]) => a.reduce((x, y) => x + y, 0),
    avg: (a: number[]) => a.reduce((x, y) => x + y, 0) / a.length,
  };

  // Setup sandbox iframe
  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;
    const html = `
      <script>
        let consoleLogs = [];
        console.log = (...a) => {
          const msg = a.map(x => JSON.stringify(x)).join(" ");
          consoleLogs.push(msg);
          parent.postMessage({ type: "log", msg }, "*");
        };
        onmessage = async (e) => {
          const { code, data, helpers } = e.data;
          consoleLogs = [];
          try {
            const fn = new Function("data", "helpers", '"use strict"; return (async ()=>{'+code+'})();');
            const result = await fn(data, helpers);
            parent.postMessage({ type: "result", ok: true, result, logs: consoleLogs }, "*");
          } catch (err) {
            parent.postMessage({ type: "result", ok: false, error: err.message, logs: consoleLogs }, "*");
          }
        };
      </script>`;
    iframe.src = URL.createObjectURL(new Blob([html], { type: "text/html" }));
  }, []);

  const runCode = () => {
    const iframe = iframeRef.current;
    if (!iframe?.contentWindow) return;

    setLogs([]);
    setResult("Running...");

    if (/\b(window|document|fetch|localStorage)\b/.test(code)) {
      setResult("❌ Disallowed API usage");
      return;
    }

    const timeout = setTimeout(() => {
      iframe.src = iframe.src; // reset sandbox
      setResult("⏱ Execution timed out");
    }, 2000);

    const listener = (e: MessageEvent<any>) => {
      if (e.data.type === "log") setLogs((prev) => [...prev, e.data.msg]);
      if (e.data.type === "result") {
        clearTimeout(timeout);
        window.removeEventListener("message", listener);
        setLogs((prev) => [...prev, ...(e.data.logs || [])]);
        setResult(e.data.ok ? JSON.stringify(e.data.result, null, 2) : "❌ " + e.data.error);
      }
    };
    window.addEventListener("message", listener);

    iframe.contentWindow.postMessage({ code, data, helpers }, "*");
  };

  return (
    <div>
      <textarea rows={8} cols={80} value={code} onChange={(e) => setCode(e.target.value)} />
      <br />
      <button onClick={runCode}>Run</button>
      <h4>Logs:</h4><pre>{logs.join("\n")}</pre>
      <h4>Result:</h4><pre>{result}</pre>
      <iframe ref={iframeRef} sandbox="allow-scripts" style={{ display: "none" }} />
    </div>
  );
};

export default FormulaSandbox;
```
