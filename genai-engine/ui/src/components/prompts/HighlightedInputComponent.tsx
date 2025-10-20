import { styled } from "@mui/material/styles";
import React, { useRef } from "react";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';

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
  value: string;
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  label?: string;
  placeholder?: string;
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange({ target: { value: e.target.value } } as React.ChangeEvent<HTMLInputElement>);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Handle special keys if needed
    if (e.key === 'Tab') {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const newValue = value.substring(0, start) + '  ' + value.substring(end);
        onChange({ target: { value: newValue } } as React.ChangeEvent<HTMLInputElement>);
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = start + 2;
        }, 0);
      }
    }
  };

  return (
    <div>
      {label && <label style={{ display: "block", marginBottom: "8px", fontSize: "0.875rem" }}>{label}</label>}
      <SyntaxHighlighterWrapper>
        <SyntaxHighlighter
          language="handlebars"
          style={oneLight}
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
          }}
          codeTagProps={{
            style: {
              background: "transparent",
              color: "inherit",
              fontSize: "inherit",
              fontFamily: "inherit",
              lineHeight: "inherit",
            }
          }}
          className="syntax-highlighter"
        >
          {value || placeholder || ""}
        </SyntaxHighlighter>
        <HiddenTextarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          {...props}
        />
      </SyntaxHighlighterWrapper>
    </div>
  );
};
