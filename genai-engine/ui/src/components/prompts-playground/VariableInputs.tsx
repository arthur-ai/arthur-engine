import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Box from "@mui/material/Box";
import { styled } from "@mui/material/styles";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import React, { useRef, useState, useEffect } from "react";

import { usePromptContext } from "./PromptsPlaygroundContext";

import { vsThemeColors } from "@/components/prompts-playground/prismTheme";

// Styled spans to match Prism VS theme syntax highlighting
const PunctuationSpan = styled("span")({
  color: vsThemeColors.punctuation,
});

const VariableSpan = styled("span")({
  color: vsThemeColors.variable,
});

const VariableInputs = () => {
  const { state, dispatch } = usePromptContext();
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollIndicator, setShowScrollIndicator] = useState(false);

  const handleKeywordValueChange = (keyword: string, value: string) => {
    dispatch({ type: "updateKeywordValue", payload: { keyword, value } });
  };

  const variables = Array.from(state.keywords.keys());

  // Check if content is scrollable
  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const checkScrollable = () => {
      const isScrollable = container.scrollHeight > container.clientHeight;
      const isAtBottom = container.scrollHeight - container.scrollTop <= container.clientHeight + 5;
      setShowScrollIndicator(isScrollable && !isAtBottom);
    };

    checkScrollable();
    container.addEventListener("scroll", checkScrollable);
    window.addEventListener("resize", checkScrollable);

    return () => {
      container.removeEventListener("scroll", checkScrollable);
      window.removeEventListener("resize", checkScrollable);
    };
  }, [variables.length]);

  const tooltipContent = (
    <Typography variant="body2">
      Variables allow you to create reusable templates by using double curly (mustache) braces like{" "}
      <PunctuationSpan>{"{"}</PunctuationSpan>
      <PunctuationSpan>{"{"}</PunctuationSpan>
      <VariableSpan>variable</VariableSpan>
      <PunctuationSpan>{"}"}</PunctuationSpan>
      <PunctuationSpan>{"}"}</PunctuationSpan>. When you define a variable below, it will automatically replace all instances of{" "}
      <PunctuationSpan>{"{"}</PunctuationSpan>
      <PunctuationSpan>{"{"}</PunctuationSpan>
      <VariableSpan>variable</VariableSpan>
      <PunctuationSpan>{"}"}</PunctuationSpan>
      <PunctuationSpan>{"}"}</PunctuationSpan> in your prompt messages. This lets you quickly test different values without editing each message individually.
    </Typography>
  );

  return (
    <Paper elevation={0} sx={{ position: "relative", height: "100%" }}>
      <Box sx={{ padding: 2 }}>
        <Stack direction="row" alignItems="center" justifyContent="center" spacing={1} className="mb-2">
          <Typography variant="h5">Variables</Typography>
          <Tooltip
            title={tooltipContent}
            arrow
            placement="bottom"
            slotProps={{
              tooltip: {
                sx: {
                  bgcolor: "#1e1e1e",
                  color: "#d4d4d4",
                  maxWidth: 500,
                  fontSize: "0.875rem",
                  "& .MuiTooltip-arrow": {
                    color: "#1e1e1e",
                  },
                },
              },
            }}
          >
            <IconButton size="small" sx={{ padding: 0.5 }}>
              <HelpOutlineIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
        <Divider className="my-2" />
      </Box>

      <Box
        ref={scrollContainerRef}
        sx={{
          maxHeight: "350px", // Approximately 6 variables worth of height
          overflowY: "auto",
          paddingX: 2,
          paddingBottom: 2,
          position: "relative",
        }}
      >
        {variables.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ padding: 2, textAlign: "center" }}>
            There are no variables present in any of your prompts. Add a variable like{" "}
            <PunctuationSpan>{"{"}</PunctuationSpan>
            <PunctuationSpan>{"{"}</PunctuationSpan>
            <VariableSpan>variable_name</VariableSpan>
            <PunctuationSpan>{"}"}</PunctuationSpan>
            <PunctuationSpan>{"}"}</PunctuationSpan> in one of your prompts to manage it here.
          </Typography>
        ) : (
          <Stack spacing={2}>
            {variables.map((variable) => (
              <TextField
                key={variable}
                id={`variable-${variable}`}
                label={variable}
                value={state.keywords.get(variable)}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                  handleKeywordValueChange(variable, e.target.value);
                }}
                variant="standard"
                fullWidth
              />
            ))}
          </Stack>
        )}
      </Box>

      {/* Scroll indicator gradient */}
      {showScrollIndicator && (
        <Box
          sx={{
            position: "absolute",
            bottom: 0,
            left: 0,
            right: 0,
            height: "40px",
            background: "linear-gradient(to top, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0) 100%)",
            pointerEvents: "none",
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "center",
            paddingBottom: 1,
          }}
        >
          <Typography variant="caption" sx={{ color: "text.secondary", fontWeight: "bold" }}>
            ↓ Scroll for more ↓
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default VariableInputs;
