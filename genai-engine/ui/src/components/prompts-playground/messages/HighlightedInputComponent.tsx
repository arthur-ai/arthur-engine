import { styled } from "@mui/material/styles";
import React, { useRef, useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";

import { OpenAIMessageItem } from "@/lib/api-client/api-client";

const SyntaxHighlighterWrapper = styled("div")({
  position: "relative",
  width: "100%",
  "& .syntax-highlighter": {
    margin: 0,
    padding: "16.5px 14px",
    fontSize: "1rem",
    fontFamily: "inherit",
    lineHeight: "1.4375em",
    border: "1px solid rgba(0, 0, 0, 0.23)",
    borderRadius: "4px",
    minHeight: "56px",
    background: "transparent !important",
    whiteSpace: "pre-wrap",
    wordWrap: "break-word",
    overflowWrap: "break-word",
    "&:focus-within": {
      borderColor: "primary.main",
      borderWidth: "2px",
    },
    "&:hover": {
      borderColor: "rgba(0, 0, 0, 0.87)",
    },
  },
  "& .syntax-highlighter code": {
    background: "transparent !important",
    color: "inherit",
    fontSize: "inherit",
    fontFamily: "inherit",
    lineHeight: "inherit",
    whiteSpace: "pre-wrap",
    wordWrap: "break-word",
    overflowWrap: "break-word",
  },
});

const FloatingLabel = styled("label")({
  position: "absolute",
  left: "14px",
  top: "16.5px",
  fontSize: "1rem",
  fontFamily: "inherit",
  lineHeight: "1.4375em",
  color: "rgba(0, 0, 0, 0.6)",
  pointerEvents: "none",
  transition: "all 0.2s ease-in-out",
  transformOrigin: "top left",
  zIndex: 3,
  "&.floating": {
    top: "-8px",
    left: "14px",
    fontSize: "0.75rem",
    backgroundColor: "white",
    padding: "0 4px",
    color: "primary.main",
  },
});

const HiddenTextarea = styled("textarea")({
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  padding: "16.5px 14px",
  fontSize: "1rem",
  fontFamily: "inherit",
  lineHeight: "1.4375em",
  border: "none",
  outline: "none",
  background: "transparent",
  color: "transparent",
  resize: "none",
  overflow: "hidden",
  whiteSpace: "pre-wrap",
  wordWrap: "break-word",
  zIndex: 1,
  caretColor: "black", // This makes the cursor visible
});

export const HighlightedInputComponent = ({
  value,
  onChange,
  label,
  placeholder,
  ...props
}: {
  value: string | OpenAIMessageItem[];
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  label?: string;
  placeholder?: string;
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isFocused, setIsFocused] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange({
      target: { value: e.target.value },
    } as React.ChangeEvent<HTMLInputElement>);
  };

  const handleFocus = () => {
    setIsFocused(true);
  };

  const handleBlur = () => {
    setIsFocused(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Handle special keys if needed
    if (e.key === "Tab") {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        // TODO: Handle OpenAIMessageItem[]
        const newValue =
          typeof value === "string"
            ? value.substring(0, start) + "  " + value.substring(end)
            : value
                .map((item) => item.text || "")
                .join(" ")
                .substring(0, start) +
              "  " +
              value
                .map((item) => item.text || "")
                .join(" ")
                .substring(end);
        onChange({
          target: { value: newValue },
        } as React.ChangeEvent<HTMLInputElement>);
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = start + 2;
        }, 0);
      }
    }
  };

  const shouldFloatLabel = isFocused || value.length > 0;

  return (
    <div>
      <SyntaxHighlighterWrapper>
        {label && <FloatingLabel className={shouldFloatLabel ? "floating" : ""}>{label}</FloatingLabel>}
        <SyntaxHighlighter
          language="handlebars"
          customStyle={{
            margin: 0,
            padding: "16.5px 14px",
            fontSize: "1rem",
            fontFamily: "inherit",
            lineHeight: "1.4375em",
            border: "1px solid rgba(0, 0, 0, 0.23)",
            borderRadius: "4px",
            minHeight: "56px",
            background: "transparent",
            whiteSpace: "pre-wrap",
            wordWrap: "break-word",
            overflowWrap: "break-word",
          }}
          codeTagProps={{
            style: {
              background: "transparent",
              color: "inherit",
              fontSize: "inherit",
              fontFamily: "inherit",
              lineHeight: "inherit",
              whiteSpace: "pre-wrap",
              wordWrap: "break-word",
              overflowWrap: "break-word",
            },
          }}
          className="syntax-highlighter"
          useInlineStyles={false}
        >
          {typeof value === "string" ? value || placeholder || "" : value.map((item) => item.text || "").join(" ") || placeholder || ""}
        </SyntaxHighlighter>
        <HiddenTextarea
          ref={textareaRef}
          value={typeof value === "string" ? value : value.map((item) => item.text || "").join(" ")}
          onChange={handleChange}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          {...props}
        />
      </SyntaxHighlighterWrapper>
    </div>
  );
};
