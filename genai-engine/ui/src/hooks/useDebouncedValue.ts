import { useEffect, useState } from "react";

/**
 * Returns a debounced version of the provided value.
 * The debounced value only updates after the specified delay has passed
 * without the source value changing.
 *
 * @param value - The value to debounce
 * @param delay - Delay in milliseconds (default: 300ms)
 * @returns The debounced value
 *
 * @example
 * const [searchText, setSearchText] = useState("");
 * const debouncedSearch = useDebouncedValue(searchText, 300);
 *
 * // Use debouncedSearch for API calls
 * useQuery({ queryKey: ["search", debouncedSearch], ... });
 */
export function useDebouncedValue<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}
