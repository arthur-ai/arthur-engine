import { MustacheHighlightedTextField } from "@arthur/shared-components";
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

  // Adapter to handle the onChange type difference
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    onChange({
      target: { value: e.target.value },
    } as React.ChangeEvent<HTMLInputElement>);
  };

  return (
    <MustacheHighlightedTextField
      value={stringValue}
      onChange={handleChange}
      placeholder={placeholder}
      multiline
      minRows={2}
      maxRows={20}
      size="small"
      hideTokens={true}
    />
  );
};
