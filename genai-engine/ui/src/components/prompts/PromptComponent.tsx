import Editor from "@monaco-editor/react";
import AddIcon from "@mui/icons-material/Add";
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteIcon from "@mui/icons-material/Delete";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import SaveIcon from "@mui/icons-material/Save";
import SettingsIcon from "@mui/icons-material/Settings";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Container from "@mui/material/Container";
import FormControl from "@mui/material/FormControl";
import IconButton from "@mui/material/IconButton";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select, { SelectChangeEvent } from "@mui/material/Select";
import Tooltip from "@mui/material/Tooltip";
import React, { useCallback, useState, useEffect } from "react";

import MessageComponent from "./MessageComponent";
import ModelParamsDialog from "./ModelParamsDialog";
import OutputField from "./OutputField";
import { PromptComponentProps } from "./types";
import { providerEnum } from "./types";

const PROVIDER_TEXT = "Provider";
const PROMPT_NAME_TEXT = "Prompt Name";
const MODEL_TEXT = "Model";

// TODO: Pull from backend
const PROMPT_NAME_OPTIONS = [
  { label: "Prompt 1", value: "prompt1" },
  { label: "Prompt 2", value: "prompt2" },
  { label: "Prompt 3", value: "prompt3" },
];

const MODEL_OPTIONS = [
  { label: "Model 1", value: "model1" },
  { label: "Model 2", value: "model2" },
  { label: "Model 3", value: "model3" },
];

/**
 * A prompt is a list of messages and templates, along with an associated output field/format.
 */
const Prompt = ({ prompt, dispatch }: PromptComponentProps) => {
  const [provider, setProvider] = useState<string>(providerEnum.OPENAI);
  const [paramsModelOpen, setParamsModelOpen] = useState<boolean>(false);
  const [toolsExpanded, setToolsExpanded] = useState<boolean>(prompt.tools.length > 0);

  // Add state to track which accordions are expanded
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

  // Track the previous tool count to detect new additions
  const [prevToolCount, setPrevToolCount] = useState(prompt.tools.length);

  const handleToggleTools = useCallback(() => {
    // Only allow toggle if there are tools
    if (prompt.tools.length > 0) {
      setToolsExpanded(!toolsExpanded);
    }
  }, [toolsExpanded, prompt.tools.length]);

  useEffect(() => {
    // Check if a new tool was added (count increased)
    if (prompt.tools.length > prevToolCount) {
      // Tools section auto-expand only if it was closed
      if (!toolsExpanded) {
        setToolsExpanded(true);
      }
      // Always set the newest tool as the one to expand
      const newestTool = prompt.tools[prompt.tools.length - 1];
      setExpandedTools(prev => new Set(prev).add(newestTool.id));
    }
    // Auto-collapse when all tools are deleted
    else if (prompt.tools.length === 0 && toolsExpanded) {
      setToolsExpanded(false);
    }
    // Update the previous count
    setPrevToolCount(prompt.tools.length);
  }, [prompt.tools, prevToolCount, toolsExpanded]);

  // Handle accordion expand/collapse
  const handleToolAccordionChange = (toolId: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpandedTools(prev => {
      const newSet = new Set(prev);
      if (isExpanded) {
        newSet.add(toolId);
      } else {
        newSet.delete(toolId);
      }
      return newSet;
    });
  };

  const handleProviderChange = (event: SelectChangeEvent) => {
    setProvider(event.target.value);
  };

  const handleDeletePrompt = useCallback(() => {
    dispatch({
      type: "deletePrompt",
      payload: { id: prompt.id },
    });
  }, [dispatch, prompt.id]);

  const handleDuplicatePrompt = useCallback(() => {
    dispatch({
      type: "duplicatePrompt",
      payload: { id: prompt.id },
    });
  }, [dispatch, prompt.id]);

  const handleAddMessage = useCallback(() => {
    dispatch({
      type: "addMessage",
      payload: { parentId: prompt.id },
    });
  }, [dispatch, prompt.id]);

  const handleParamsModelOpen = useCallback(() => {
    setParamsModelOpen(true);
  }, []);

  const handleDeleteTool = useCallback((toolId: string) => {
    dispatch({
      type: "deleteTool",
      payload: { parentId: prompt.id, toolId },
    });
  }, [dispatch, prompt.id]);

  const handleToolChange = useCallback((toolId: string, newValue: string) => {
    try {
      const parsedTool = JSON.parse(newValue);
      dispatch({
        type: "updateTool",
        payload: { 
          parentId: prompt.id, 
          toolId, 
          tool: {
            ...parsedTool,
            id: toolId
          }
        },
      });
    } catch (error) {
      console.error("Invalid JSON:", error);
    }
  }, [dispatch, prompt.id]);

  return (
    <div className="bg-purple-500 min-h-[500px]">
      <Container component="div" className="p-1" maxWidth="xl" disableGutters>
        <div className="grid grid-cols-2 gap-1">
          <div className="flex justify-start items-center gap-1">
            <div className="w-1/3">
              <FormControl fullWidth size="small" variant="filled">
                <InputLabel id={`prompt-name-${prompt.id}`}>
                  {PROMPT_NAME_TEXT}
                </InputLabel>
                <Select
                  labelId={`prompt-name-${prompt.id}`}
                  id={`prompt-name-${prompt.id}`}
                  label={PROMPT_NAME_TEXT}
                  value={PROMPT_NAME_OPTIONS[0].value}
                  onChange={() => {}}
                >
                  {PROMPT_NAME_OPTIONS.map((promptNameOption) => (
                    <MenuItem
                      key={promptNameOption.value}
                      value={promptNameOption.value}
                    >
                      {promptNameOption.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </div>
            <div className="w-1/3">
              <FormControl fullWidth size="small" variant="filled">
                <InputLabel id={`provider-${prompt.id}`}>
                  {PROVIDER_TEXT}
                </InputLabel>
                <Select
                  labelId={`provider-${prompt.id}`}
                  id={`provider-${prompt.id}`}
                  label={PROVIDER_TEXT}
                  value={provider}
                  onChange={handleProviderChange}
                >
                  {Object.values(providerEnum).map((providerValue) => (
                    <MenuItem key={providerValue} value={providerValue}>
                      {providerValue}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </div>
            <div className="w-1/3">
              <FormControl fullWidth size="small" variant="filled">
                <InputLabel id={`model-${prompt.id}`}>{MODEL_TEXT}</InputLabel>
                <Select
                  labelId={`model-${prompt.id}`}
                  id={`model-${prompt.id}`}
                  label={MODEL_TEXT}
                  value={MODEL_OPTIONS[0].value}
                  onChange={() => {}}
                >
                  {MODEL_OPTIONS.map((modelOption) => (
                    <MenuItem key={modelOption.value} value={modelOption.value}>
                      {modelOption.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </div>
          </div>
          <div className="flex justify-end items-center gap-1">
            <Tooltip title="Add Message" placement="top-start" arrow>
              <IconButton aria-label="add" onClick={handleAddMessage}>
                <AddIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Duplicate Prompt" placement="top-start" arrow>
              <IconButton
                aria-label="duplicate"
                onClick={handleDuplicatePrompt}
              >
                <ContentCopyIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Model Parameters" placement="top-start" arrow>
              <IconButton
                aria-label="model parameters"
                onClick={handleParamsModelOpen}
              >
                <SettingsIcon />
              </IconButton>
            </Tooltip>
            <ModelParamsDialog
              open={paramsModelOpen}
              setOpen={setParamsModelOpen}
              promptId={prompt.id}
              name={prompt.name}
              modelParameters={prompt.modelParameters}
              dispatch={dispatch}
            />
            <Tooltip title="Save Prompt" placement="top-start" arrow>
              <IconButton aria-label="save" onClick={() => {}}>
                <SaveIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="Delete Prompt" placement="top-start" arrow>
              <IconButton aria-label="delete" onClick={handleDeletePrompt}>
                <DeleteIcon />
              </IconButton>
            </Tooltip>
          </div>
        </div>
      </Container>
      <div>
        {prompt.messages.map((message) => (
          <MessageComponent
            key={message.id}
            id={message.id}
            parentId={prompt.id}
            role={message.role}
            defaultContent={message.content}
            content={message.content}
            dispatch={dispatch}
          />
        ))}
      </div>
      <div className="m-1">
        <Paper elevation={2} className="p-1">
          <div 
            className={`flex justify-between items-center p-2 bg-white text-gray-800 rounded ${
              prompt.tools.length > 0 ? 'cursor-pointer' : 'cursor-default'
            }`}
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
          </div>
          {toolsExpanded && (
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
                      backgroundColor: '#d1d5db',
                      color: '#374151',
                      minHeight: '32px'
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
                        style={{ color: '#374151', width: '24px', height: '24px' }}
                      >
                        <DeleteIcon fontSize="small" />
                      </div>
                    </div>
                  </AccordionSummary>
                  <AccordionDetails sx={{ padding: 0 }}>
                    <div style={{ height: '300px', width: '100%' }}>
                      <Editor
                        height="300px"
                        defaultLanguage="json"
                        theme="light"
                        value={JSON.stringify({
                          type: tool.type,
                          function: tool.function
                        }, null, 2)}
                        onChange={(value) => {
                          if (value) {
                            handleToolChange(tool.id, value);
                          }
                        }}
                        options={{
                          minimap: { enabled: false },
                          lineNumbers: 'on',
                          fontSize: 12,
                          tabSize: 2,
                          automaticLayout: true
                        }}
                      />
                    </div>
                  </AccordionDetails>
                </Accordion>
              ))}
            </div>
          )}
        </Paper>
      </div>
      <div className="m-1">
        <Paper elevation={2} className="p-1">
          <OutputField
            promptId={prompt.id}
            responseFormat={prompt.responseFormat}
            dispatch={dispatch}
          />
        </Paper>
      </div>
    </div>
  );
};

export default Prompt;
