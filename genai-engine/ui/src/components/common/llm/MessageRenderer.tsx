import { Collapsible } from "@base-ui-components/react/collapsible";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { Box, Button, ButtonGroup, Paper, Stack, Typography } from "@mui/material";
import { useState } from "react";

import { Highlight } from "../Highlight";

import { TextMessageRenderer } from "./TextMessageRenderer";

import { type Message, type ToolCall } from "@/schemas/llm";
import { getRoleAccentColor, tryFormatJson } from "@/utils/llm";

const MAX_HEIGHT = 350;

// ============================================================================
// Value Rendering Components
// ============================================================================

const renderValue = (value: any): React.ReactNode => {
  if (value === null) return "null";
  if (value === undefined) return "undefined";
  if (Array.isArray(value)) {
    return <ArrayValue array={value} />;
  }
  if (typeof value === "object") {
    return <ObjectValue obj={value} />;
  }
  if (typeof value === "string") return `"${value}"`;
  return String(value);
};

const ArrayValue = ({ array }: { array: any[] }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (array.length === 0) return <>[]</>;

  return (
    <Box component="span">
      <Box
        component="span"
        onClick={() => setIsOpen(!isOpen)}
        sx={{
          cursor: "pointer",
          userSelect: "none",
          "&:hover": { opacity: 0.7 },
        }}
      >
        {isOpen ? "▼" : "▶"} Array[{array.length}]
      </Box>
      {isOpen && (
        <Box component="ul" sx={{ m: 0, mt: 0.5, p: 0, pl: 3, listStyle: "none" }}>
          {array.map((item, index) => (
            <Box component="li" key={index} sx={{ mb: 0.5, fontSize: 11 }}>
              <Typography component="span" fontWeight={600} fontSize={11} color="text.secondary">
                [{index}]:
              </Typography>{" "}
              <Typography component="span" fontSize={11} sx={{ fontFamily: "monospace" }}>
                {renderValue(item)}
              </Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
};

const ObjectValue = ({ obj }: { obj: Record<string, any> }) => {
  const [isOpen, setIsOpen] = useState(false);
  const keys = Object.keys(obj);

  if (keys.length === 0) return <>{"{}"}</>;

  return (
    <Box component="span">
      <Box
        component="span"
        onClick={() => setIsOpen(!isOpen)}
        sx={{
          cursor: "pointer",
          userSelect: "none",
          "&:hover": { opacity: 0.7 },
        }}
      >
        {isOpen ? "▼" : "▶"} Object
      </Box>
      {isOpen && (
        <Box component="ul" sx={{ m: 0, mt: 0.5, p: 0, pl: 3, listStyle: "none" }}>
          {Object.entries(obj).map(([key, value]) => (
            <Box component="li" key={key} sx={{ mb: 0.5, fontSize: 11 }}>
              <Typography component="span" fontWeight={600} fontSize={11} color="text.secondary">
                {key}:
              </Typography>{" "}
              <Typography component="span" fontSize={11} sx={{ fontFamily: "monospace" }}>
                {renderValue(value)}
              </Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
};

const KeyValueList = ({ data }: { data: Record<string, any> }) => (
  <Box component="ul" sx={{ m: 0, p: 0, pl: 2, listStyle: "none" }}>
    {Object.entries(data).map(([key, value]) => (
      <Box component="li" key={key} sx={{ mb: 0.5, fontSize: 11 }}>
        <Typography component="span" fontWeight={600} fontSize={11} color="text.secondary">
          {key}:
        </Typography>{" "}
        <Typography component="span" fontSize={11} sx={{ fontFamily: "monospace" }}>
          {renderValue(value)}
        </Typography>
      </Box>
    ))}
  </Box>
);

// ============================================================================
// UI Components
// ============================================================================

const ViewToggle = ({ view, setView }: { view: "formatted" | "raw"; setView: (view: "formatted" | "raw") => void }) => (
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
);

const ContentBox = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <Box>
    <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{ mb: 1, display: "block" }}>
      {label}
    </Typography>
    <Paper variant="outlined" sx={{ p: 2, maxHeight: MAX_HEIGHT, overflow: "auto" }}>
      {children}
    </Paper>
  </Box>
);

// ============================================================================
// Content Renderers
// ============================================================================

/**
 * Parses a string as JSON, returning null if parsing fails
 */
const parseJson = (content: string): any | null => {
  try {
    return JSON.parse(content);
  } catch {
    return null;
  }
};

/**
 * Renders tool result content with automatic JSON detection and formatting
 */
const ToolContentRenderer = ({ content }: { content: string }) => {
  const [view, setView] = useState<"formatted" | "raw">("formatted");
  const parsedContent = parseJson(content);
  const isJson = parsedContent !== null && typeof parsedContent === "object";

  return (
    <ContentBox label="Tool Result">
      {!isJson ? (
        <TextMessageRenderer text={content} unwrapped />
      ) : (
        <>
          <ViewToggle view={view} setView={setView} />
          {view === "formatted" ? (
            <KeyValueList data={parsedContent} />
          ) : (
            <Highlight code={tryFormatJson(content)} language="json" unwrapped />
          )}
        </>
      )}
    </ContentBox>
  );
};

/**
 * Renders a single tool call with its arguments
 */
const ToolCallItem = ({ toolCall }: { toolCall: ToolCall }) => {
  const parsedArgs = toolCall.tool_call.function.arguments
    ? parseJson(toolCall.tool_call.function.arguments)
    : null;

  return (
    <Box>
      <Typography variant="body2" fontWeight={600} fontSize={12} mb={1}>
        {toolCall.tool_call.function.name}
      </Typography>
      <Box sx={{ pl: 2 }}>
        {parsedArgs && typeof parsedArgs === "object" ? (
          <KeyValueList data={parsedArgs} />
        ) : (
          <Typography fontSize={11} color="text.secondary">
            (no arguments)
          </Typography>
        )}
      </Box>
    </Box>
  );
};

/**
 * Renders a list of tool calls with formatted/raw view toggle
 */
const ToolCallsRenderer = ({ toolCalls }: { toolCalls: ToolCall[] }) => {
  const [view, setView] = useState<"formatted" | "raw">("formatted");

  return (
    <>
      <ViewToggle view={view} setView={setView} />
      {view === "formatted" ? (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {toolCalls.map((toolCall, index) => (
            <ToolCallItem key={index} toolCall={toolCall} />
          ))}
        </Box>
      ) : (
        <Highlight code={tryFormatJson(toolCalls)} language="json" unwrapped />
      )}
    </>
  );
};

// ============================================================================
// Content Type Renderers
// ============================================================================

/**
 * Renders assistant message content with optional tool calls
 */
const AssistantMessageContent = ({ message }: { message: Extract<Message, { role: "assistant" }> }) => {
  const { content, tool_calls } = message;
  const hasContent = content && content !== "";
  const hasToolCalls = tool_calls && tool_calls.length > 0;

  if (!hasToolCalls) {
    return (
      <ContentBox label="Content">
        <TextMessageRenderer text={content || ""} unwrapped />
      </ContentBox>
    );
  }

  if (hasContent && hasToolCalls) {
    return (
      <>
        <ContentBox label="Content">
          <TextMessageRenderer text={content} unwrapped />
        </ContentBox>
        <Box sx={{ mt: 2 }}>
          <ContentBox label="Tool Calls">
            <ToolCallsRenderer toolCalls={tool_calls} />
          </ContentBox>
        </Box>
      </>
    );
  }

  return (
    <ContentBox label="Tool Calls">
      <ToolCallsRenderer toolCalls={tool_calls} />
    </ContentBox>
  );
};

/**
 * Renders array content (multimodal messages)
 */
const ArrayMessageContent = ({ content }: { content: any[] }) => (
  <ContentBox label="Contents">
    {content.map((item, index) => {
      switch (item.type) {
        case "text":
          return <TextMessageRenderer key={index} text={item.text} unwrapped />;
        default:
          return <Highlight key={index} code={tryFormatJson(item)} language="json" unwrapped />;
      }
    })}
  </ContentBox>
);

/**
 * Renders string content with role-specific formatting
 */
const StringMessageContent = ({ role, content }: { role: Message["role"]; content: string }) => {
  if (role === "tool") {
    return <ToolContentRenderer content={content} />;
  }

  return (
    <ContentBox label="Content">
      <TextMessageRenderer text={content} unwrapped />
    </ContentBox>
  );
};

/**
 * Determines and renders the appropriate content based on message structure
 */
const MessageContent = ({ message }: { message: Message }) => {
  const { role, content } = message;

  // Assistant messages with potential tool calls
  if (role === "assistant" && "tool_calls" in message) {
    return <AssistantMessageContent message={message} />;
  }

  // Array content (multimodal)
  if (Array.isArray(content) && content.length > 0) {
    return <ArrayMessageContent content={content} />;
  }

  // String content
  if (typeof content === "string" && content !== "") {
    return <StringMessageContent role={role} content={content} />;
  }

  return null;
};

// ============================================================================
// Main Message Renderer
// ============================================================================

export const MessageRenderer = ({ message }: { message: Message }) => {
  const { role } = message;
  const contentToRender = <MessageContent message={message} />;

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
            {getRoleLabel(role)}
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

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Returns a human-readable label for a message role
 */
const getRoleLabel = (role: Message["role"]): string => {
  const labels: Record<Message["role"], string> = {
    system: "System",
    user: "User",
    assistant: "Assistant",
    tool: "Tool",
  };
  return labels[role] || role;
};
