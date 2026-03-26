import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import { Box, Chip, CircularProgress, keyframes, Paper, Table, Tooltip, Typography } from "@mui/material";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { ChatMessage as ChatMessageType, ToolCallEvent } from "@/hooks/useChatbot";

interface ChatMessageProps {
  message: ChatMessageType;
}

function shortenPath(path: string): string {
  const taskMatch = path.match(/\/api\/v\d+\/tasks\/[^/]+\/(.*)/);
  if (taskMatch) return taskMatch[1];
  return path.replace(/^\/api\/v\d+/, "");
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  if (message.role === "tool_call") {
    const success = message.status_code !== undefined && message.status_code < 400;
    const fullLabel = `${message.method} ${message.path}`;
    const shortLabel = `${message.method} ${shortenPath(message.path ?? "")}`;
    return (
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1, pl: 0.5, minWidth: 0 }}>
        {success ? (
          <CheckCircleOutlineIcon sx={{ fontSize: 14, color: "success.main", flexShrink: 0 }} />
        ) : (
          <ErrorOutlineIcon sx={{ fontSize: 14, color: "error.main", flexShrink: 0 }} />
        )}
        <Tooltip title={fullLabel} placement="top">
          <Chip
            label={shortLabel}
            size="small"
            variant="outlined"
            color={success ? "success" : "error"}
            sx={{
              fontFamily: "monospace",
              fontSize: "0.7rem",
              maxWidth: "100%",
              "& .MuiChip-label": { overflow: "hidden", textOverflow: "ellipsis" },
            }}
          />
        </Tooltip>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        mb: 1.5,
      }}
    >
      <Paper
        elevation={0}
        sx={{
          px: 2,
          py: 1.5,
          maxWidth: "80%",
          bgcolor: isUser ? "primary.main" : "action.hover",
          color: isUser ? "primary.contrastText" : "text.primary",
          borderRadius: isUser ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
          wordBreak: "break-word",
        }}
      >
        {isUser ? (
          <Typography variant="body2">{message.content}</Typography>
        ) : (
          <Typography
            variant="body2"
            component="div"
            sx={{
              "& th, & td": {
                border: "1px solid",
                borderColor: "divider",
                px: 1,
                py: 0.5,
                maxWidth: 400,
                whiteSpace: "normal",
                wordBreak: "break-word",
              },
            }}
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                table: ({ children }) => (
                  <Box sx={{ overflowX: "auto" }}>
                    <Table sx={{ borderCollapse: "collapse", width: "max-content" }}>{children}</Table>
                  </Box>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </Typography>
        )}
      </Paper>
    </Box>
  );
}

interface ToolCallIndicatorProps {
  toolCall: ToolCallEvent;
}

export function ToolCallIndicator({ toolCall }: ToolCallIndicatorProps) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1.5, pl: 0.5 }}>
      <CircularProgress size={14} />
      <Chip label={`${toolCall.method} ${toolCall.path}`} size="small" variant="outlined" sx={{ fontFamily: "monospace", fontSize: "0.7rem" }} />
    </Box>
  );
}

const bounce = keyframes`
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-4px); opacity: 1; }
`;

export function ThinkingIndicator() {
  return (
    <Box sx={{ display: "flex", justifyContent: "flex-start", mb: 1.5 }}>
      <Paper elevation={0} sx={{ px: 2, py: 1.5, bgcolor: "action.hover", borderRadius: "12px 12px 12px 2px" }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          {[0, 1, 2].map((i) => (
            <Box
              key={i}
              sx={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                bgcolor: "text.secondary",
                animation: `${bounce} 1.2s ease-in-out infinite`,
                animationDelay: `${i * 0.2}s`,
              }}
            />
          ))}
        </Box>
      </Paper>
    </Box>
  );
}
