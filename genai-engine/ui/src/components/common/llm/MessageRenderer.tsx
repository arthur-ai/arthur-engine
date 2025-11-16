import { Collapsible } from "@base-ui-components/react/collapsible";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { Box, Paper, Stack, Typography } from "@mui/material";

import { Highlight } from "../Highlight";

import { TextMessageRenderer } from "./TextMessageRenderer";

import { type Message } from "@/schemas/llm";
import { getRoleAccentColor, tryFormatJson } from "@/utils/llm";

export const MessageRenderer = ({ message }: { message: Message }) => {
  const { role, content } = message;

  let contentToRender = null;
  
  // Check if this is an assistant message with tool_calls but empty content
  if (
    role === "assistant" && 
    "tool_calls" in message && 
    message.tool_calls && 
    message.tool_calls.length > 0 &&
    (!content || content === "")
  ) {
    // Render tool calls as pretty-printed JSON
    contentToRender = (
      <Highlight 
        code={tryFormatJson(message.tool_calls)} 
        language="json" 
      />
    );
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
