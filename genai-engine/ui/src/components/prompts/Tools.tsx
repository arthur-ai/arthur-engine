import Editor from "@monaco-editor/react";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import DeleteIcon from "@mui/icons-material/Delete";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  Accordion,
  AccordionSummary,
  Collapse,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  SelectChangeEvent,
} from "@mui/material";
import { AccordionDetails } from "@mui/material";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import React, { useCallback, useEffect, useState } from "react";

import { PromptAction, PromptType } from "./types";

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

const Tools = ({
  dispatch,
  prompt,
}: {
  dispatch: (action: PromptAction) => void;
  prompt: PromptType;
}) => {
  const [toolsExpanded, setToolsExpanded] = useState<boolean>(
    prompt.tools.length > 0
  );

  // Add state to track which accordions are expanded
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

  // Track the previous tool count to detect new additions
  const [prevToolCount, setPrevToolCount] = useState(prompt.tools.length);

  const handleAddTool = useCallback(() => {
    dispatch({
      type: "addTool",
      payload: { promptId: prompt.id },
    });
  }, [dispatch, prompt.id]);

  const handleToggleTools = useCallback(() => {
    // Only allow toggle if there are tools
    if (prompt.tools.length > 0) {
      setToolsExpanded((prev) => !prev);
    }
  }, [prompt.tools.length]);

  useEffect(() => {
    // Check if a new tool was added (count increased)
    if (prompt.tools.length > prevToolCount) {
      // Tools section auto-expand only if it was closed
      if (!toolsExpanded) {
        setToolsExpanded(true);
      }
      // Always set the newest tool as the one to expand
      const newestTool = prompt.tools[prompt.tools.length - 1];
      setExpandedTools((prev) => new Set(prev).add(newestTool.id));
    }
    // Auto-collapse when all tools are deleted
    else if (prompt.tools.length === 0 && toolsExpanded) {
      setToolsExpanded(false);
    }
    // Update the previous count
    setPrevToolCount(prompt.tools.length);
  }, [prompt.tools, prevToolCount, toolsExpanded]);

  // Handle accordion expand/collapse
  const handleToolAccordionChange =
    (toolId: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
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
    (event: SelectChangeEvent) => {
      dispatch({
        type: "updateToolChoice",
        payload: { promptId: prompt.id, toolChoice: event.target.value },
      });
    },
    [dispatch, prompt.id]
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

  const pointerClass =
    prompt.tools.length > 0 ? "cursor-pointer" : "cursor-default";
  return (
    <>
      <div
        className={`flex justify-between items-center ${pointerClass}`}
        onClick={handleToggleTools}
      >
        <div className="flex items-center gap-2">
          {toolsExpanded ? <ExpandMoreIcon /> : <ChevronRightIcon />}
          <span className="font-medium">Tools</span>
          {prompt.tools.length > 0 && (
            <span className="bg-gray-300 px-2 py-1 rounded text-sm">
              {prompt.tools.length}
            </span>
          )}
        </div>
        <Button variant="contained" size="small" onClick={handleAddTool}>
          Add Tools
        </Button>
      </div>
      <Collapse in={toolsExpanded}>
      <div className="mt-2 mb-3 px-2">
          <FormControl size="small" fullWidth sx={{ maxWidth: 400 }}>
            <InputLabel>Tool Choice</InputLabel>
            <Select
              value={prompt.toolChoice}
              label="Tool Choice"
              onChange={handleToolChoiceChange}
              renderValue={(selected) => {
                if (["auto", "none", "required"].includes(selected)) {
                  return renderToolChoiceOption(selected);
                } else {
                  const selectedTool = prompt.tools.find(
                    (tool) => tool.id === selected
                  );
                  return selectedTool
                    ? renderToolChoiceOption(
                        selected,
                        selectedTool.function.name
                      )
                    : selected;
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
              <MenuItem value="required">
                {renderToolChoiceOption("required")}
              </MenuItem>
              {prompt.tools.length > 0 && [
                ...prompt.tools.map((tool) => (
                  <MenuItem key={tool.id} value={tool.id}>
                    {renderToolChoiceOption(tool.id, tool.function.name)}
                  </MenuItem>
                )),
              ]}
            </Select>
          </FormControl>
        </div>
        <div className="space-y-2 mt-2">
          {prompt.tools.map((tool) => (
            <Accordion
              key={tool.id}
              expanded={expandedTools.has(tool.id)}
              onChange={handleToolAccordionChange(tool.id)}
            >
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                sx={{
                  backgroundColor: "#d1d5db",
                  color: "#374151",
                  minHeight: "32px",
                }}
              >
                <div className="flex items-center justify-between w-full mr-4">
                  <span className="text-sm font-mono">
                    📋 {tool.function.name}
                  </span>
                  <div
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteTool(tool.id);
                    }}
                    className="p-1 rounded hover:bg-gray-300 cursor-pointer flex items-center justify-center"
                    style={{ color: "#374151", width: "24px", height: "24px" }}
                  >
                    <DeleteIcon fontSize="small" />
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
                        type: tool.type,
                        function: tool.function,
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
      </Collapse>
    </>
  );
};

export default Tools;
