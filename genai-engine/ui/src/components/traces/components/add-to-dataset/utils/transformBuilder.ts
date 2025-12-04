import { Column, TransformDefinition } from "../form/shared";

// Builds transform definition from columns using the stored span_name and attribute_path
export function buildTransformFromColumns(columns: Column[]): TransformDefinition {
  return {
    variables: columns
      .filter((col) => col.span_name && col.attribute_path && col.name)
      .map((col) => {
        return {
          variable_name: col.name,
          span_name: col.span_name!,
          attribute_path: col.attribute_path!,
          fallback: null,
        };
      }),
  };
}

export function validateTransform(transform: TransformDefinition): string[] {
  const errors: string[] = [];

  if (!transform.variables || transform.variables.length === 0) {
    errors.push("Transform must have at least one variable");
    return errors;
  }

  const variableNames = new Set<string>();
  for (const varDef of transform.variables) {
    if (!varDef.variable_name) {
      errors.push("Variable name is required");
      continue;
    }

    if (variableNames.has(varDef.variable_name)) {
      errors.push(`Duplicate variable name: ${varDef.variable_name}`);
    }
    variableNames.add(varDef.variable_name);

    if (!varDef.span_name) {
      errors.push(`Variable ${varDef.variable_name}: span_name is required`);
    }

    if (!varDef.attribute_path) {
      errors.push(`Variable ${varDef.variable_name}: attribute_path is required`);
    }
  }

  return errors;
}
