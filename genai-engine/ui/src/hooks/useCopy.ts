type Opts = {
  onCopy?: (text: string) => void;
  onError?: (error: Error) => void;
};

export const useCopy = (opts: Opts) => {
  const { onCopy, onError } = opts;

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      onCopy?.(text);
    } catch (error) {
      if (error instanceof Error) {
        onError?.(error);
      } else {
        onError?.(new Error("Failed to copy to clipboard"));
      }
    }
  };

  return { handleCopy };
};
