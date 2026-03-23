/**
 * Filters out null and undefined values from an object
 * This ensures that only explicitly set parameters are sent to the backend,
 * allowing provider defaults to be used for unset parameters
 */
const filterNullParams = <T extends Record<string, unknown>>(params: T): Partial<T> => {
  const filtered: Partial<T> = {};
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined) {
      filtered[key as keyof T] = value as T[keyof T];
    }
  }
  return filtered;
};

export default filterNullParams;
