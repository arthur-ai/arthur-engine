type Opts = {
  onCopy?: (text: string) => void;
  onError?: (error: Error) => void;
};

const copyToClipboard = async (text: string): Promise<void> => {
  if (navigator.clipboard) {
    await navigator.clipboard.writeText(text);
    return;
  }
  // Fallback for non-secure contexts (HTTP) where navigator.clipboard is unavailable
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.style.position = "fixed";
  textArea.style.left = "-9999px";
  textArea.style.top = "-9999px";
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();
  const success = document.execCommand("copy");
  document.body.removeChild(textArea);
  if (!success) {
    throw new Error("Failed to copy to clipboard");
  }
};

export const useCopy = (opts: Opts) => {
  const { onCopy, onError } = opts;

  const handleCopy = async (text: string) => {
    try {
      await copyToClipboard(text);
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
