import { Column, TransformDefinition } from "../form/shared";

// Builds transform definition from columns. Parses "SpanName.attributes.key" into span_name and attribute_path.
export function buildTransformFromColumns(columns: Column[]): TransformDefinition {
  return {
    version: "1.0",
    columns: columns
      .filter((col) => col.path && col.name)
      .map((col) => {
        const parts = col.path.split(".");
        const span_name = parts[0];
        const attribute_path = parts.slice(1).join(".");

        return {
          column_name: col.name,
          span_name,
          attribute_path,
          fallback: null,
        };
      }),
  };
}

// Validates transform definition, returns array of error messages (empty if valid)
export function validateTransform(transform: TransformDefinition): string[] {
  const errors: string[] = [];

  if (!transform.columns || transform.columns.length === 0) {
    errors.push("Transform must have at least one column");
    return errors;
  }

  const columnNames = new Set<string>();
  for (const col of transform.columns) {
    if (!col.column_name) {
      errors.push("Column name is required");
      continue;
    }

    if (columnNames.has(col.column_name)) {
      errors.push(`Duplicate column name: ${col.column_name}`);
    }
    columnNames.add(col.column_name);

    if (!col.span_name) {
      errors.push(`Column ${col.column_name}: span_name is required`);
    }

    if (!col.attribute_path) {
      errors.push(`Column ${col.column_name}: attribute_path is required`);
    }
  }

  return errors;
}

