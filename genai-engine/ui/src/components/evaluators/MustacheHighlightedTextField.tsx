import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import { styled } from "@mui/material/styles";
import React, { useMemo, useRef, useCallback, useEffect } from "react";

interface MustacheHighlightedTextFieldProps {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  multiline?: boolean;
  minRows?: number;
  maxRows?: number;
  size?: "small" | "medium";
}

const EditableDiv = styled("div")(({ theme }) => ({
  width: "100%",
  minHeight: "80px",
  maxHeight: "250px",
  overflow: "auto",
  padding: "8.5px 14px",
  fontSize: "0.8125rem",
  fontFamily: "monospace",
  lineHeight: "1.4375em",
  color: "rgba(0, 0, 0, 0.87)",
  backgroundColor: "white",
  border: "1px solid rgba(0, 0, 0, 0.23)",
  borderRadius: "4px",
  outline: "none",
  whiteSpace: "pre-wrap",
  wordWrap: "break-word",
  transition: "border-color 0.2s",
  "&:hover": {
    borderColor: "rgba(0, 0, 0, 0.87)",
  },
  "&:focus": {
    borderColor: "#1976d2",
    borderWidth: "2px",
    padding: "7.5px 13px", // Adjust padding to compensate for border width
  },
  "&[data-placeholder]:empty:before": {
    content: "attr(data-placeholder)",
    color: "rgba(0, 0, 0, 0.38)",
    pointerEvents: "none",
  },
  "& .mustache-var": {
    color: "#1976d2",
    fontWeight: 400,
    backgroundColor: "rgba(180, 190, 165, 0.2)",
    padding: "2px 4px",
    borderRadius: "3px",
  },
}));

const MustacheHighlightedTextField: React.FC<MustacheHighlightedTextFieldProps> = ({
  value,
  onChange,
  placeholder,
  disabled = false,
  required = false,
  multiline = true,
  minRows = 4,
  maxRows = 10,
  size = "small",
}) => {
  const editableRef = useRef<HTMLDivElement>(null);
  const isUpdatingRef = useRef(false);

  // Extract all mustache variables from the text
  const mustacheVariables = useMemo(() => {
    if (!value) return [];
    const matches = value.match(/\{\{[^}]+\}\}/g);
    if (!matches) return [];
    return Array.from(new Set(matches));
  }, [value]);

  // Generate highlighted HTML
  const generateHighlightedHtml = useCallback((text: string) => {
    if (!text) return "";

    const escapeHtml = (str: string) => {
      return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    };

    const escaped = escapeHtml(text);

    // Split by mustache patterns to preserve exact text structure
    const parts = escaped.split(/(\{\{[^}]+\}\})/g);

    return parts
      .map((part) => {
        if (part.match(/\{\{[^}]+\}\}/)) {
          // This is a mustache variable - highlight it
          return `<span class="mustache-var">${part}</span>`;
        }
        // Regular text - no wrapper needed, let parent handle color
        return part;
      })
      .join("");
  }, []);

  // Save and restore cursor position
  const saveCursorPosition = useCallback(() => {
    const selection = window.getSelection();
    if (!selection || !editableRef.current || selection.rangeCount === 0) return 0;

    const range = selection.getRangeAt(0);
    const preCaretRange = range.cloneRange();
    preCaretRange.selectNodeContents(editableRef.current);
    preCaretRange.setEnd(range.endContainer, range.endOffset);
    return preCaretRange.toString().length;
  }, []);

  const restoreCursorPosition = useCallback((position: number) => {
    if (!editableRef.current || position === 0) return;

    const selection = window.getSelection();
    if (!selection) return;

    let charCount = 0;
    const nodeStack: Node[] = [editableRef.current];
    let node: Node | undefined;

    while ((node = nodeStack.pop())) {
      if (node.nodeType === Node.TEXT_NODE) {
        const textLength = node.textContent?.length || 0;
        if (charCount + textLength >= position) {
          try {
            const range = document.createRange();
            range.setStart(node, Math.min(position - charCount, textLength));
            range.collapse(true);
            selection.removeAllRanges();
            selection.addRange(range);
          } catch (e) {
            // Cursor restoration failed, ignore
          }
          break;
        }
        charCount += textLength;
      } else {
        for (let i = node.childNodes.length - 1; i >= 0; i--) {
          nodeStack.push(node.childNodes[i]);
        }
      }
    }
  }, []);

  // Update highlighting
  const updateHighlighting = useCallback(() => {
    if (!editableRef.current || isUpdatingRef.current) return;

    isUpdatingRef.current = true;
    const cursorPos = saveCursorPosition();
    const currentText = editableRef.current.innerText || "";
    const newHtml = generateHighlightedHtml(currentText);

    editableRef.current.innerHTML = newHtml;
    restoreCursorPosition(cursorPos);
    isUpdatingRef.current = false;
  }, [generateHighlightedHtml, saveCursorPosition, restoreCursorPosition]);

  const handleInput = useCallback(() => {
    if (editableRef.current && !isUpdatingRef.current) {
      const newValue = editableRef.current.innerText || "";

      // Create a synthetic event
      const syntheticEvent = {
        target: { value: newValue },
        currentTarget: { value: newValue },
      } as React.ChangeEvent<HTMLTextAreaElement>;

      onChange(syntheticEvent);

      // Update highlighting after a short delay to allow the change to propagate
      setTimeout(() => updateHighlighting(), 0);
    }
  }, [onChange, updateHighlighting]);

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    e.preventDefault();
    const text = e.clipboardData.getData("text/plain");
    document.execCommand("insertText", false, text);
  }, []);

  // Initialize content when value changes externally
  useEffect(() => {
    if (editableRef.current && !isUpdatingRef.current) {
      const currentText = editableRef.current.innerText || "";
      if (currentText !== value) {
        const cursorPos = saveCursorPosition();
        editableRef.current.innerHTML = generateHighlightedHtml(value);
        restoreCursorPosition(cursorPos);
      }
    }
  }, [value, generateHighlightedHtml, saveCursorPosition, restoreCursorPosition]);

  return (
    <Box sx={{ width: "100%" }}>
      <EditableDiv
        ref={editableRef}
        contentEditable={!disabled}
        onInput={handleInput}
        onPaste={handlePaste}
        data-placeholder={placeholder}
        suppressContentEditableWarning
        style={{
          cursor: disabled ? "not-allowed" : "text",
          opacity: disabled ? 0.6 : 1,
        }}
      />

      {/* Display found variables as chips below */}
      {mustacheVariables.length > 0 && (
        <Box
          sx={{
            mt: 1,
            display: "flex",
            flexWrap: "wrap",
            gap: 0.5,
            alignItems: "center",
          }}
        >
          <Box
            component="span"
            sx={{
              fontSize: "0.75rem",
              color: "text.secondary",
              mr: 0.5,
            }}
          >
            Variables:
          </Box>
          {mustacheVariables.map((variable, index) => (
            <Chip
              key={index}
              label={variable}
              size="small"
              sx={{
                height: 20,
                fontSize: "0.7rem",
                fontFamily: "monospace",
                backgroundColor: "rgba(180, 190, 165, 0.2)",
                color: "#1976d2",
                fontWeight: 400,
                "& .MuiChip-label": {
                  px: 1,
                  py: 0,
                  lineHeight: "20px",
                },
              }}
            />
          ))}
        </Box>
      )}
    </Box>
  );
};

export default MustacheHighlightedTextField;
