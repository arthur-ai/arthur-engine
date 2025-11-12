/**
 * Extracts context from attributes if available (OpenInference format)
 */
const extractContext = (attributes: Record<string, unknown>): Record<string, unknown>[] | null => {
  // Check for OpenInference context in attributes
  const input = attributes.input as { value?: unknown } | undefined;
  if (input?.value && Array.isArray(input.value)) {
    return input.value as Record<string, unknown>[];
  }
  // Check for other context formats
  if (attributes.context && Array.isArray(attributes.context)) {
    return attributes.context as Record<string, unknown>[];
  }
  return null;
};

export default extractContext;
