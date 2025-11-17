import { Collapsible } from "@base-ui-components/react/collapsible";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { Box, Button, ButtonGroup, Paper, Stack, Typography } from "@mui/material";
import { useState } from "react";

import { Highlight } from "../Highlight";

import { TextMessageRenderer } from "./TextMessageRenderer";

import { type Message, type ToolCall } from "@/schemas/llm";
import { getRoleAccentColor, tryFormatJson } from "@/utils/llm";

const ToolCallsRenderer = ({ toolCalls }: { toolCalls: ToolCall[] }) => {
  const [view, setView] = useState<"formatted" | "raw">("formatted");

  const parseArguments = (args?: string) => {
    if (!args) return null;
    try {
      return JSON.parse(args);
    } catch {
      return null;
    }
  };

  const renderArgumentValue = (value: any): string => {
    if (value === null) return "null";
    if (value === undefined) return "undefined";
    if (typeof value === "object") return JSON.stringify(value);
    if (typeof value === "string") return `"${value}"`;
    return String(value);
  };

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "flex-end", mb: 1 }}>
        <ButtonGroup size="small" variant="outlined">
          <Button
            onClick={() => setView("formatted")}
            variant={view === "formatted" ? "contained" : "outlined"}
            sx={{ fontSize: 10, py: 0.5, px: 1 }}
          >
            Formatted
          </Button>
          <Button
            onClick={() => setView("raw")}
            variant={view === "raw" ? "contained" : "outlined"}
            sx={{ fontSize: 10, py: 0.5, px: 1 }}
          >
            Raw
          </Button>
        </ButtonGroup>
      </Box>
      {view === "formatted" ? (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {toolCalls.map((toolCall, index) => {
            const parsedArgs = parseArguments(toolCall.tool_call.function.arguments);
            return (
              <Box key={index}>
                <Typography variant="body2" fontWeight={600} fontSize={12} mb={1}>
                  {toolCall.tool_call.function.name}
                </Typography>
                <Box sx={{ pl: 2 }}>
                  {parsedArgs && typeof parsedArgs === "object" ? (
                    <Box component="ul" sx={{ m: 0, p: 0, listStyle: "none" }}>
                      {Object.entries(parsedArgs).map(([key, value]) => (
                        <Box component="li" key={key} sx={{ mb: 0.5, fontSize: 11 }}>
                          <Typography component="span" fontWeight={600} fontSize={11} color="text.secondary">
                            {key}:
                          </Typography>{" "}
                          <Typography component="span" fontSize={11} sx={{ fontFamily: "monospace" }}>
                            {renderArgumentValue(value)}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  ) : (
                    <Typography fontSize={11} color="text.secondary">
                      (no arguments)
                    </Typography>
                  )}
                </Box>
              </Box>
            );
          })}
        </Box>
      ) : (
        <Highlight code={tryFormatJson(toolCalls)} language="json" />
      )}
    </Box>
  );
};

export const MessageRenderer = ({ message }: { message: Message }) => {
  const { role, content } = message;

  let contentToRender = null;

  // Check if this is an assistant message with tool_calls
  if (
    role === "assistant" &&
    "tool_calls" in message &&
    message.tool_calls &&
    message.tool_calls.length > 0
  ) {
    // Render both content and tool calls if content exists
    if (content && content !== "") {
      contentToRender = (
        <>
          <TextMessageRenderer text={content} />
          <Box sx={{ mt: 2 }}>
            <ToolCallsRenderer toolCalls={message.tool_calls} />
          </Box>
        </>
      );
    } else {
      // Only tool calls, no content
      contentToRender = <ToolCallsRenderer toolCalls={message.tool_calls} />;
    }
  } else if (Array.isArray(content) && content.length > 0) {
    contentToRender = content.map((item, index) => {
      switch (item.type) {
        case "text":
          return <TextMessageRenderer key={index} text={item.text} />;
        default:
          return (
            <Highlight key={index} code={tryFormatJson(item)} language="json" />
          );
      }
    });
  } else if (typeof content === "string" && content !== "") {
    contentToRender = <TextMessageRenderer text={content} />;
  }

  return (
    <Collapsible.Root
      defaultOpen
      render={
        <Paper
          variant="outlined"
          sx={{
            fontSize: "12px",
            textWrap: "wrap",
            overflow: "auto",
          }}
        />
      }
    >
      <Collapsible.Trigger className="group w-full" disabled={!contentToRender}>
        <Stack
          direction="row"
          alignItems="center"
          gap={1}
          p={1}
          sx={{
            borderColor: "divider",
            backgroundColor: getRoleAccentColor(role),
            textAlign: "left",
          }}
          className="group-data-panel-open:border-b group-disabled:opacity-25"
        >
          <KeyboardArrowRightIcon
            fontSize="small"
            className="group-data-panel-open:rotate-90 transition-transform duration-75"
          />
          <Typography color="text.primary" fontWeight={600} fontSize={12}>
            {getRoleLabel(role, message)}
          </Typography>
        </Stack>
      </Collapsible.Trigger>
      {contentToRender ? (
        <Collapsible.Panel>
          <Box p={1}>{contentToRender}</Box>
        </Collapsible.Panel>
      ) : null}
    </Collapsible.Root>
  );
};

function getRoleLabel(role: Message["role"], message: Message) {
  switch (role) {
    case "system":
      return "System";
    case "user":
      return "User";
    case "assistant":
      return "Assistant";
    case "tool":
      return "Tool";
    default:
      return role;
  }
}
