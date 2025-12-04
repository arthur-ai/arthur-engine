import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import { styled } from "@mui/material/styles";
import React, { useMemo, useRef, useCallback, useEffect } from "react";

// Jinja2/Nunjucks keywords and control structures that should NOT be treated as variables
const JINJA_2_KEYWORDS = new Set([
  "if",
  "elif",
  "else",
  "endif",
  "for",
  "endfor",
  "in",
  "block",
  "endblock",
  "extends",
  "include",
  "import",
  "from",
  "macro",
  "endmacro",
  "call",
  "endcall",
  "filter",
  "endfilter",
  "set",
  "endset",
  "raw",
  "endraw",
  "with",
  "endwith",
  "autoescape",
  "endautoescape",
  "trans",
  "endtrans",
  "pluralize",
  "do",
  "break",
  "continue",
  "scoped",
  "ignore",
  "missing",
  "and",
  "or",
  "not",
  "is",
  "in",
  "true",
  "false",
  "none",
  "True",
  "False",
  "None",
]);

interface NunjucksHighlightedTextFieldProps {
  value: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  multiline?: boolean;
  minRows?: number;
  maxRows?: number;
  size?: "small" | "medium";
  readOnly?: boolean;
  hideTokens?: boolean;
}

interface SelectionPosition {
  start: number;
  end: number;
  isCollapsed: boolean;
}

const EditableDiv = styled("div")(() => ({
  width: "100%",
  height: "100%",
  minHeight: "80px",
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
  "& .nunjucks-var": {
    color: "#1976d2",
    fontWeight: 400,
    backgroundColor: "rgba(180, 190, 165, 0.2)",
    padding: "2px 4px",
    borderRadius: "3px",
  },
  "& .nunjucks-tag": {
    color: "#7c3aed",
    fontWeight: 400,
    backgroundColor: "rgba(124, 58, 237, 0.12)",
    padding: "2px 4px",
    borderRadius: "3px",
  },
}));

const NunjucksHighlightedTextField: React.FC<NunjucksHighlightedTextFieldProps> = ({
  value,
  onChange,
  placeholder,
  disabled = false,
  readOnly = false,
  hideTokens = false,
}) => {
  const editableRef = useRef<HTMLDivElement>(null);
  const isUpdatingRef = useRef(false);
  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isEditingRef = useRef(false);

  // Function to find and highlight a specific token in the editor
  const highlightToken = useCallback((tokenToFind: string) => {
    if (!editableRef.current) return;

    const text = editableRef.current.innerText || "";
    const index = text.indexOf(tokenToFind);

    if (index === -1) return;

    // Find the text node and position
    const selection = window.getSelection();
    if (!selection) return;

    let charCount = 0;
    const nodeStack: Node[] = [editableRef.current];
    let node: Node | undefined;
    let found = false;

    while ((node = nodeStack.pop()) && !found) {
      if (node.nodeType === Node.TEXT_NODE) {
        const textLength = node.textContent?.length || 0;
        if (charCount + textLength >= index) {
          try {
            const range = document.createRange();
            const startOffset = index - charCount;
            const endOffset = Math.min(startOffset + tokenToFind.length, textLength);
            range.setStart(node, startOffset);
            range.setEnd(node, endOffset);

            // Add the range to selection
            selection.removeAllRanges();
            selection.addRange(range);

            // Prevent default scroll-into-view behavior by using preventScroll option on focus
            editableRef.current.focus({ preventScroll: true });

            // Use scrollIntoView with block: 'center' on the selection
            // This is the simplest and most reliable approach
            requestAnimationFrame(() => {
              if (!selection.rangeCount) return;

              const currentRange = selection.getRangeAt(0);

              // Create a temporary element to scroll to
              const tempElement = document.createElement("span");
              currentRange.insertNode(tempElement);

              // Scroll the element into the center of the view
              tempElement.scrollIntoView({
                behavior: "smooth",
                block: "center",
                inline: "nearest",
              });

              // Clean up the temp element and restore selection
              setTimeout(() => {
                if (tempElement.parentNode) {
                  const parentNode = tempElement.parentNode;
                  const textNode = node;
                  parentNode.removeChild(tempElement);

                  // Restore the selection if we still have the node
                  if (editableRef.current && textNode) {
                    try {
                      const newRange = document.createRange();
                      newRange.setStart(textNode, startOffset);
                      newRange.setEnd(textNode, endOffset);
                      selection.removeAllRanges();
                      selection.addRange(newRange);
                    } catch {
                      // Selection restoration failed, ignore
                    }
                  }
                }
              }, 10);
            });

            found = true;
          } catch {
            // Selection failed, ignore
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

  // Extract all Nunjucks variables and statements from the text
  const nunjucksTokens = useMemo(() => {
    if (!value) return { variables: [], statements: [] };

    // Match variables {{ variable }}
    const variableMatches = value.match(/\{\{[^}]+\}\}/g);
    const allVariables = variableMatches ? Array.from(new Set(variableMatches)) : [];

    // Filter out variables that are just Jinja2 keywords
    const variables = allVariables.filter((varToken) => {
      // Extract the content between {{ and }}
      const content = varToken.replace(/^\{\{\s*|\s*\}\}$/g, "").trim();

      // Split by spaces, dots, pipes, and other operators to get individual tokens
      const tokens = content.split(/[\s.|()[\]\],+\-*/%=!<>&|]+/).filter((t) => t.length > 0);

      // Check if the first token (main identifier) is a keyword
      const mainToken = tokens[0];

      // If it's a pure keyword with no other context, filter it out
      if (tokens.length === 1 && JINJA_2_KEYWORDS.has(mainToken)) {
        return false;
      }

      return true;
    });

    // Match control flow statements {% if %}, {% for %}, etc.
    const statementMatches = value.match(/\{%[^%]+%\}/g);
    const statements = statementMatches ? Array.from(new Set(statementMatches)) : [];

    return { variables, statements };
  }, [value]);

  // Generate highlighted HTML
  const generateHighlightedHtml = useCallback((text: string) => {
    if (!text) return "";

    const escapeHtml = (str: string) => {
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    };

    const escaped = escapeHtml(text);

    // Split by both Nunjucks patterns: variables {{ }} and statements {% %}
    const parts = escaped.split(/(\{\{[^}]+\}\}|\{%[^%]+%\})/g);

    return parts
      .map((part) => {
        if (part.match(/\{\{[^}]+\}\}/)) {
          // This is a Nunjucks variable - highlight in blue
          return `<span class="nunjucks-var">${part}</span>`;
        } else if (part.match(/\{%[^%]+%\}/)) {
          // This is a Nunjucks statement (control flow) - highlight in purple
          return `<span class="nunjucks-tag">${part}</span>`;
        }
        // Regular text - no wrapper needed, let parent handle color
        return part;
      })
      .join("");
  }, []);

  // Save and restore cursor/selection position
  const saveCursorPosition = useCallback((): SelectionPosition | null => {
    const selection = window.getSelection();
    if (!selection || !editableRef.current || selection.rangeCount === 0) {
      return null;
    }

    const range = selection.getRangeAt(0);
    const isCollapsed = range.collapsed;

    // Calculate start position
    const startRange = range.cloneRange();
    startRange.selectNodeContents(editableRef.current);
    startRange.setEnd(range.startContainer, range.startOffset);
    const start = startRange.toString().length;

    // Calculate end position
    const endRange = range.cloneRange();
    endRange.selectNodeContents(editableRef.current);
    endRange.setEnd(range.endContainer, range.endOffset);
    const end = endRange.toString().length;

    return { start, end, isCollapsed };
  }, []);

  // Helper function to find text node and offset at a given character position
  const findTextNodeAtPosition = useCallback((position: number): { node: Text; offset: number } | null => {
    if (!editableRef.current) return null;

    let charCount = 0;
    const nodeStack: Node[] = [editableRef.current];
    let node: Node | undefined;

    while ((node = nodeStack.pop())) {
      if (node.nodeType === Node.TEXT_NODE) {
        const textLength = node.textContent?.length || 0;
        if (charCount + textLength >= position) {
          return {
            node: node as Text,
            offset: Math.min(position - charCount, textLength),
          };
        }
        charCount += textLength;
      } else {
        for (let i = node.childNodes.length - 1; i >= 0; i--) {
          nodeStack.push(node.childNodes[i]);
        }
      }
    }
    return null;
  }, []);

  const restoreCursorPosition = useCallback(
    (position: SelectionPosition | null, forceCollapseToStart: boolean = false) => {
      if (!editableRef.current || !position) return;

      const selection = window.getSelection();
      if (!selection) return;

      const startResult = findTextNodeAtPosition(position.start);
      if (!startResult) return;

      try {
        const range = document.createRange();

        // If collapsed or force collapse, just set start position
        if (position.isCollapsed || forceCollapseToStart) {
          range.setStart(startResult.node, startResult.offset);
          range.collapse(true);
        } else {
          // Restore selection range
          const endResult = findTextNodeAtPosition(position.end);
          if (endResult) {
            range.setStart(startResult.node, startResult.offset);
            range.setEnd(endResult.node, endResult.offset);
          } else {
            // Fallback to collapsed if end position not found
            range.setStart(startResult.node, startResult.offset);
            range.collapse(true);
          }
        }

        selection.removeAllRanges();
        selection.addRange(range);
      } catch {
        // Cursor restoration failed, ignore
      }
    },
    [findTextNodeAtPosition]
  );

  // Update highlighting
  const updateHighlighting = useCallback(() => {
    if (!editableRef.current || isUpdatingRef.current || isEditingRef.current) return;

    isUpdatingRef.current = true;
    const cursorPos = saveCursorPosition();
    const currentText = editableRef.current.innerText || "";
    const newHtml = generateHighlightedHtml(currentText);

    editableRef.current.innerHTML = newHtml;
    restoreCursorPosition(cursorPos, false);
    isUpdatingRef.current = false;
  }, [generateHighlightedHtml, saveCursorPosition, restoreCursorPosition]);

  const handleInput = useCallback(() => {
    if (editableRef.current && !isUpdatingRef.current && !readOnly && onChange) {
      const newValue = editableRef.current.innerText || "";

      // Create a synthetic event
      const syntheticEvent = {
        target: { value: newValue },
        currentTarget: { value: newValue },
      } as React.ChangeEvent<HTMLTextAreaElement>;

      onChange(syntheticEvent);

      // Clear any pending highlighting update
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }

      // Debounce highlighting update with shorter delay for better responsiveness
      debounceTimeoutRef.current = setTimeout(() => {
        isEditingRef.current = false;
        updateHighlighting();
        debounceTimeoutRef.current = null;
      }, 150);
    }
  }, [onChange, updateHighlighting, readOnly]);

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    e.preventDefault();
    const text = e.clipboardData.getData("text/plain");

    // Split text by newlines and insert using insertLineBreak for proper handling
    const lines = text.split("\n");

    lines.forEach((line, index) => {
      if (index > 0) {
        // Insert a line break before each line except the first
        document.execCommand("insertLineBreak");
      }
      if (line.length > 0) {
        // Insert the text content
        document.execCommand("insertText", false, line);
      }
    });
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    // Detect deletion keys to prevent highlighting updates during active deletion
    if (e.key === "Backspace" || e.key === "Delete") {
      isEditingRef.current = true;
    }

    // Handle Enter key to ensure proper new line insertion
    if (e.key === "Enter") {
      e.preventDefault();
      document.execCommand("insertLineBreak");

      // Scroll cursor into view after inserting line break
      requestAnimationFrame(() => {
        const selection = window.getSelection();
        if (selection && selection.rangeCount > 0) {
          const range = selection.getRangeAt(0);

          // Insert a temporary span at cursor position to measure and scroll
          const tempSpan = document.createElement("span");
          tempSpan.innerHTML = "&nbsp;"; // Use non-breaking space so it has height
          range.insertNode(tempSpan);

          // Scroll the temp span into view
          tempSpan.scrollIntoView({ behavior: "auto", block: "nearest" });

          // Remove the temp span and restore cursor position
          const parent = tempSpan.parentNode;
          if (parent) {
            parent.removeChild(tempSpan);
            // Cursor should already be in the right place after removing the span
          }
        }
      });
    }
  }, []);

  // Initialize content when value changes externally
  useEffect(() => {
    if (editableRef.current && !isUpdatingRef.current) {
      const currentText = editableRef.current.innerText || "";
      if (currentText !== value) {
        const cursorPos = saveCursorPosition();
        editableRef.current.innerHTML = generateHighlightedHtml(value);
        restoreCursorPosition(cursorPos, false);
      }
    }
  }, [value, generateHighlightedHtml, saveCursorPosition, restoreCursorPosition]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, []);

  return (
    <Box sx={{ width: "100%", height: "100%", display: "flex", flexDirection: "column" }}>
      <EditableDiv
        ref={editableRef}
        contentEditable={!disabled && !readOnly}
        onInput={handleInput}
        onPaste={handlePaste}
        onKeyDown={handleKeyDown}
        data-placeholder={placeholder}
        suppressContentEditableWarning
        style={{
          cursor: disabled || readOnly ? "default" : "text",
          backgroundColor: disabled ? "#f5f5f5" : readOnly ? "transparent" : "white",
          border: readOnly ? "none" : undefined,
          padding: readOnly ? "0" : undefined,
        }}
      />

      {/* Display found variables and statements as chips below */}
      {!hideTokens && (nunjucksTokens.variables.length > 0 || nunjucksTokens.statements.length > 0) && (
        <Box
          sx={{
            mt: 1,
            display: "flex",
            flexWrap: "wrap",
            gap: 0.5,
            alignItems: "center",
          }}
        >
          {nunjucksTokens.variables.length > 0 && (
            <>
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
              {nunjucksTokens.variables.map((variable: string, index: number) => (
                <Chip
                  key={`var-${index}`}
                  label={variable}
                  size="small"
                  onClick={() => highlightToken(variable)}
                  sx={{
                    height: 20,
                    fontSize: "0.7rem",
                    fontFamily: "monospace",
                    backgroundColor: "rgba(180, 190, 165, 0.2)",
                    color: "#1976d2",
                    fontWeight: 400,
                    cursor: "pointer",
                    "&:hover": {
                      backgroundColor: "rgba(180, 190, 165, 0.35)",
                    },
                    "& .MuiChip-label": {
                      px: 1,
                      py: 0,
                      lineHeight: "20px",
                    },
                  }}
                />
              ))}
            </>
          )}

          {nunjucksTokens.statements.length > 0 && (
            <>
              <Box
                component="span"
                sx={{
                  fontSize: "0.75rem",
                  color: "text.secondary",
                  mr: 0.5,
                  ml: nunjucksTokens.variables.length > 0 ? 1 : 0,
                }}
              >
                Statements:
              </Box>
              {nunjucksTokens.statements.map((statement: string, index: number) => (
                <Chip
                  key={`statement-${index}`}
                  label={statement}
                  size="small"
                  onClick={() => highlightToken(statement)}
                  sx={{
                    height: 20,
                    fontSize: "0.7rem",
                    fontFamily: "monospace",
                    backgroundColor: "rgba(124, 58, 237, 0.12)",
                    color: "#7c3aed",
                    fontWeight: 400,
                    cursor: "pointer",
                    "&:hover": {
                      backgroundColor: "rgba(124, 58, 237, 0.22)",
                    },
                    "& .MuiChip-label": {
                      px: 1,
                      py: 0,
                      lineHeight: "20px",
                    },
                  }}
                />
              ))}
            </>
          )}
        </Box>
      )}
    </Box>
  );
};

export default NunjucksHighlightedTextField;
