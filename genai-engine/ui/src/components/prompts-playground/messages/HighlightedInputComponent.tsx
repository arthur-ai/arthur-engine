import TextField from "@mui/material/TextField";
import React from "react";

import { OpenAIMessageItem } from "@/lib/api-client/api-client";

export const HighlightedInputComponent = ({
  value,
  onChange,
  placeholder,
}: {
  value: string | OpenAIMessageItem[];
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
}) => {
  // Convert OpenAIMessageItem[] to string
  const stringValue = typeof value === "string" ? value : value.map((item) => item.text || "").join(" ");

  return (
    <TextField
      value={stringValue}
      onChange={(e) => onChange(e as React.ChangeEvent<HTMLInputElement>)}
      placeholder={placeholder}
      variant="filled"
      multiline
      minRows={2}
      maxRows={20}
      size="small"
      fullWidth
    />
  );
};
