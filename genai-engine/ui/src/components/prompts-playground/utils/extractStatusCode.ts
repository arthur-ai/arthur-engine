/**
 * Extracts status code from status field (can be array, object, or string)
 */
const extractStatusCode = (status: unknown[] | { code?: string | number } | string | undefined): string => {
  if (!status) {
    return "Unset";
  }
  if (typeof status === "string") {
    return status;
  }
  if (Array.isArray(status)) {
    if (status.length === 0) {
      return "Unset";
    }
    const first = status[0];
    if (typeof first === "object" && first !== null && "code" in first) {
      const code = first.code;
      if (typeof code === "string") return code;
      if (typeof code === "number") {
        // Map numeric codes: 1=Ok, 2=Error, 0/undefined=Unset
        if (code === 1) return "Ok";
        if (code === 2) return "Error";
        return "Unset";
      }
    }
    return "Unset";
  }
  if (typeof status === "object" && status !== null && "code" in status) {
    const code = status.code;
    if (typeof code === "string") return code;
    if (typeof code === "number") {
      if (code === 1) return "Ok";
      if (code === 2) return "Error";
      return "Unset";
    }
  }
  return "Unset";
};

export default extractStatusCode;
