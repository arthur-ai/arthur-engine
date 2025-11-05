import Editor from "@monaco-editor/react";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select, { SelectChangeEvent } from "@mui/material/Select";
import Tooltip from "@mui/material/Tooltip";
import React, { useCallback, useEffect, useState } from "react";

import { usePromptContext } from "../PromptsPlaygroundContext";
import { PromptType } from "../types";
import { getToolChoiceDisplayValue } from "../utils";

import { ToolChoiceEnum, ToolChoice } from "@/lib/api-client/api-client";

const validToolEnumValues = ["auto", "none", "required"] as const;

// Helper function to render tool choice options consistently
const renderToolChoiceOption = (value: string, toolName?: string) => {
  const isSpecificTool = !["auto", "none", "required"].includes(value);

  const textMap: Record<string, string> = {
    auto: "Let LLM decide",
    none: "Don't use tools",
    required: "Use one or more tools",
  };

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
      <span>{textMap[value] || toolName || value}</span>
      <Chip
        label={isSpecificTool ? "tool" : value}
        size="small"
        sx={{
          backgroundColor: isSpecificTool ? "#dbeafe" : "#e5e7eb",
          color: isSpecificTool ? "#1e40af" : "#374151",
          height: "20px",
          fontSize: "0.75rem",
        }}
      />
    </Box>
  );
};

interface ToolsDialogProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  prompt: PromptType;
}

const ToolsDialog = ({ open, setOpen, prompt }: ToolsDialogProps) => {
  const { dispatch } = usePromptContext();
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());
  const [prevToolCount, setPrevToolCount] = useState(prompt.tools.length);

  const handleClose = useCallback(() => {
    setOpen(false);
  }, [setOpen]);

  const handleAddTool = useCallback(() => {
    dispatch({
      type: "addTool",
      payload: { promptId: prompt.id },
    });
  }, [dispatch, prompt.id]);

  // Handle accordion expand/collapse
  const handleToolAccordionChange = (toolId: string) => (_event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpandedTools((prev) => {
      const newSet = new Set(prev);
      if (isExpanded) {
        newSet.add(toolId);
      } else {
        newSet.delete(toolId);
      }
      return newSet;
    });
  };

  const handleDeleteTool = useCallback(
    (toolId: string) => {
      dispatch({
        type: "deleteTool",
        payload: { promptId: prompt.id, toolId },
      });
    },
    [dispatch, prompt.id]
  );

  const handleToolChoiceChange = useCallback(
    (event: SelectChangeEvent<string>) => {
      const selectedValue = event.target.value;

      // If it's one of the predefined selections, set as ToolChoiceEnum
      if (validToolEnumValues.includes(selectedValue as ToolChoiceEnum)) {
        dispatch({
          type: "updateToolChoice",
          payload: { promptId: prompt.id, toolChoice: selectedValue as ToolChoiceEnum },
        });
      } else {
        // Otherwise, it's a tool ID - find the tool and convert to ToolChoice object
        const selectedTool = prompt.tools.find((tool) => tool.id === selectedValue);
        if (selectedTool) {
          const toolChoice: ToolChoice = {
            function: {
              name: selectedTool.function.name,
            },
            type: "function",
          };
          dispatch({
            type: "updateToolChoice",
            payload: { promptId: prompt.id, toolChoice },
          });
        }
      }
    },
    [dispatch, prompt.id, prompt.tools]
  );

  const handleToolChange = useCallback(
    (toolId: string, newValue: string) => {
      try {
        const parsedTool = JSON.parse(newValue);
        dispatch({
          type: "updateTool",
          payload: {
            parentId: prompt.id,
            toolId,
            tool: {
              ...parsedTool,
              id: toolId,
            },
          },
        });
      } catch (error) {
        console.error("Invalid JSON:", error);
      }
    },
    [dispatch, prompt.id]
  );

  // Auto-expand newly added tools when modal is open
  useEffect(() => {
    if (open && prompt.tools.length > prevToolCount) {
      const newestTool = prompt.tools[prompt.tools.length - 1];
      setExpandedTools((prev) => new Set(prev).add(newestTool.id));
    }
    setPrevToolCount(prompt.tools.length);
  }, [open, prompt.tools, prevToolCount]);

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="md">
      <DialogTitle>
        <div className="flex justify-between items-center">
          <span>Tools</span>
          <Button variant="contained" onClick={handleAddTool} startIcon={<AddIcon />}>
            Add Tool
          </Button>
        </div>
      </DialogTitle>
      <DialogContent>
        <div className="mb-4 mt-3">
          <FormControl size="small" fullWidth sx={{ maxWidth: 400 }}>
            <InputLabel>Tool Choice</InputLabel>
            <Select
              value={getToolChoiceDisplayValue(prompt.toolChoice, prompt.tools)}
              label="Tool Choice"
              onChange={handleToolChoiceChange}
              renderValue={(selected) => {
                if (validToolEnumValues.includes(selected as ToolChoiceEnum)) {
                  return renderToolChoiceOption(selected);
                } else {
                  const selectedTool = prompt.tools.find((tool) => tool.id === selected);
                  return selectedTool ? renderToolChoiceOption(selected, selectedTool.function.name) : selected;
                }
              }}
              sx={{
                backgroundColor: "white",
                "& .MuiOutlinedInput-root": {
                  backgroundColor: "white",
                },
              }}
            >
              <MenuItem value="auto">{renderToolChoiceOption("auto")}</MenuItem>
              <MenuItem value="none">{renderToolChoiceOption("none")}</MenuItem>
              <MenuItem value="required">{renderToolChoiceOption("required")}</MenuItem>
              {prompt.tools.length > 0 &&
                prompt.tools.map((tool) => (
                  <MenuItem key={tool.id} value={tool.id}>
                    {renderToolChoiceOption(tool.id, tool.function.name)}
                  </MenuItem>
                ))}
            </Select>
          </FormControl>
        </div>
        <div className="space-y-2">
          {prompt.tools.map((tool) => (
            <Accordion key={tool.id} expanded={expandedTools.has(tool.id)} onChange={handleToolAccordionChange(tool.id)}>
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                sx={{
                  backgroundColor: "#d1d5db",
                  color: "#374151",
                  minHeight: "32px",
                  flexDirection: "row-reverse",
                  "& .MuiAccordionSummary-expandIconWrapper": {
                    transform: "rotate(-90deg)",
                  },
                  "& .MuiAccordionSummary-expandIconWrapper.Mui-expanded": {
                    transform: "rotate(0deg)",
                  },
                }}
              >
                <div className="flex items-center justify-between w-full mr-4">
                  <span className="text-sm font-mono">📋 {tool.function.name}</span>
                  <div
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteTool(tool.id);
                    }}
                    className="p-1 rounded hover:bg-gray-300 cursor-pointer flex items-center justify-center"
                    style={{ color: "#374151", width: "24px", height: "24px" }}
                  >
                    <Tooltip title="Delete Tool" placement="top-start" arrow>
                      <DeleteIcon fontSize="small" color="error" />
                    </Tooltip>
                  </div>
                </div>
              </AccordionSummary>
              <AccordionDetails sx={{ padding: 0 }}>
                <div style={{ height: "300px", width: "100%" }}>
                  <Editor
                    height="300px"
                    defaultLanguage="json"
                    theme="light"
                    value={JSON.stringify(
                      {
                        function: {
                          name: tool.function.name,
                          description: tool.function.description,
                          parameters: tool.function.parameters,
                        },
                        strict: tool.strict,
                        type: tool.type,
                      },
                      null,
                      2
                    )}
                    onChange={(value) => {
                      if (value) {
                        handleToolChange(tool.id, value);
                      }
                    }}
                    options={{
                      minimap: { enabled: false },
                      lineNumbers: "on",
                      fontSize: 12,
                      tabSize: 2,
                      automaticLayout: true,
                    }}
                  />
                </div>
              </AccordionDetails>
            </Accordion>
          ))}
        </div>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default ToolsDialog;
