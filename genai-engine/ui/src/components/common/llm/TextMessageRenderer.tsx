import {
  Paper,
  Table,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Render a text message as a markdown component.
 * @param text - The text to render.
 * @returns The rendered markdown component.
 */
export const TextMessageRenderer = ({ text }: { text: string }) => {
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: ({ children }) => (
            <TableContainer component={Paper} variant="outlined" sx={{ my: 2 }}>
              <Table size="small">{children}</Table>
            </TableContainer>
          ),
          thead: ({ children }) => (
            <TableHead
              sx={{
                backgroundColor: "grey.50",
              }}
            >
              {children}
            </TableHead>
          ),
          tr: ({ children }) => <TableRow hover>{children}</TableRow>,
          td: ({ children }) => <TableCell>{children}</TableCell>,
          th: ({ children }) => <TableCell>{children}</TableCell>,
        }}
      >
        {text}
      </Markdown>
    </Paper>
  );
};
