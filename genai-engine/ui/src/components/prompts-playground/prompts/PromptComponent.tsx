import Alert from "@mui/material/Alert";
import Badge from "@mui/material/Badge";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Snackbar from "@mui/material/Snackbar";
import Tooltip from "@mui/material/Tooltip";
import AddIcon from "@mui/icons-material/Add";
import BuildIcon from "@mui/icons-material/Build";
import CodeIcon from "@mui/icons-material/Code";
import React, { useCallback, useEffect, useState, useRef } from "react";

import MessagesSection from "../messages/MessagesSection";
import { usePromptContext } from "../PromptsPlaygroundContext";
import { PromptComponentProps } from "../types";

import ManagementButtons from "./ManagementButtons";
import OutputField from "./OutputField";
import PromptSelectors from "./PromptSelectors";
import ResizableSplitter from "./ResizableSplitter";
import SavePromptDialog from "./SavePromptDialog";
import ToolsDialog from "./ToolsDialog";

import useRunPrompt from "@/components/prompts-playground/hooks/useRunPrompt";
import useContainerWidth from "@/components/prompts-playground/hooks/useContainerWidth";
import useSnackbar from "@/hooks/useSnackbar";

/**
 * A prompt is a list of messages and templates, along with an associated output field/format.
 */
const Prompt = ({ prompt, useIconOnlyMode: useIconOnlyModeProp }: PromptComponentProps) => {
  // This name value updates when an existing prompt is selected
  const [currentPromptName, setCurrentPromptName] = useState<string>(prompt.name || "");
  const [nameInputValue, setNameInputValue] = useState("");
  const [savePromptOpen, setSavePromptOpen] = useState<boolean>(false);
  const [toolsDialogOpen, setToolsDialogOpen] = useState<boolean>(false);
  const [responseSchemaDialogOpen, setResponseSchemaDialogOpen] = useState<boolean>(false);
  const [messagesHeightRatio, setMessagesHeightRatio] = useState<number>(0.7); // Default: 70% messages, 30% response
  const containerRef = useRef<HTMLDivElement>(null);
  const outerRef = useRef<HTMLDivElement>(null);
  const hasTriggeredRunRef = useRef<boolean>(false);
  const { showSnackbar, snackbarProps, alertProps } = useSnackbar();

  const { dispatch } = usePromptContext();

  // Use container width to determine icon-only mode (container queries approach)
  // Switch to icon-only mode when container is less than 600px wide
  // This ensures buttons don't overlap when space is constrained
  const containerWidth = useContainerWidth(outerRef);
  const useIconOnlyMode = useIconOnlyModeProp || (containerWidth > 0 && containerWidth < 600);

  const runPrompt = useRunPrompt({
    prompt,
    onError: (error) => {
      showSnackbar(error, "error");
    },
  });

  const handleAddMessage = () => {
    dispatch({
      type: "addMessage",
      payload: { parentId: prompt.id },
    });
  };

  const handleOpenResponseSchemaDialog = () => {
    setResponseSchemaDialogOpen(true);
  };

  useEffect(() => {
    setNameInputValue(currentPromptName);
  }, [currentPromptName]);

  useEffect(() => {
    if (prompt.running && !hasTriggeredRunRef.current) {
      hasTriggeredRunRef.current = true;
      runPrompt();
    } else if (!prompt.running && hasTriggeredRunRef.current) {
      hasTriggeredRunRef.current = false;
    }
  }, [prompt.running, runPrompt]);

  const handleResize = useCallback((newRatio: number) => {
    setMessagesHeightRatio(newRatio);
  }, []);

  return (
    <div ref={outerRef} className="h-full shadow-md rounded-lg p-1 bg-gray-200 flex flex-col">
      <Container component="div" ref={containerRef} className="p-1 mt-1 flex flex-col h-full" maxWidth="lg" disableGutters>
        <div className="flex justify-between items-center gap-1 mb-2 flex-shrink-0">
          <div className="flex justify-start items-center gap-1 min-w-0">
            {useIconOnlyMode ? (
              <>
                {/* Icon-only mode when space is constrained */}
                {prompt.tools.length > 0 ? (
                  <Badge badgeContent={prompt.tools.length} color="primary">
                    <Tooltip title="Tools" arrow>
                      <IconButton size="small" onClick={() => setToolsDialogOpen(true)}>
                        <BuildIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Badge>
                ) : (
                  <Tooltip title="Tools" arrow>
                    <IconButton size="small" onClick={() => setToolsDialogOpen(true)}>
                      <BuildIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                )}
                <Tooltip title="Add Message" arrow>
                  <IconButton size="small" onClick={handleAddMessage}>
                    <AddIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Format Response" arrow>
                  <IconButton size="small" onClick={handleOpenResponseSchemaDialog}>
                    <CodeIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </>
            ) : (
              <>
                {/* Full buttons with text when there's space */}
                {prompt.tools.length > 0 ? (
                  <Badge badgeContent={prompt.tools.length} color="primary">
                    <Button variant="outlined" size="small" onClick={() => setToolsDialogOpen(true)} startIcon={<BuildIcon />} sx={{ minWidth: "auto", px: 1 }}>
                      Tools
                    </Button>
                  </Badge>
                ) : (
                  <Button variant="outlined" size="small" onClick={() => setToolsDialogOpen(true)} startIcon={<BuildIcon />} sx={{ minWidth: "auto", px: 1 }}>
                    Tools
                  </Button>
                )}
                <Button variant="outlined" size="small" onClick={handleAddMessage} startIcon={<AddIcon />} sx={{ minWidth: "auto", px: 1, whiteSpace: "nowrap" }}>
                  Add Message
                </Button>
                <Button variant="outlined" size="small" onClick={handleOpenResponseSchemaDialog} startIcon={<CodeIcon />} sx={{ minWidth: "auto", px: 1, whiteSpace: "nowrap" }}>
                  Format Response
                </Button>
              </>
            )}
          </div>
          <div className="flex justify-end items-center gap-1 flex-shrink-0">
            <ManagementButtons prompt={prompt} setSavePromptOpen={setSavePromptOpen} />
          </div>
        </div>
        <div className="flex-shrink-0 min-w-0">
          <PromptSelectors prompt={prompt} currentPromptName={currentPromptName} onPromptNameChange={setCurrentPromptName} />
        </div>
        <div className="mt-1 flex-1 min-h-0 flex flex-col">
          <div
            className="flex-shrink-0"
            style={{
              flexBasis: `${messagesHeightRatio * 100}%`,
              minHeight: "30%",
            }}
          >
            <Paper elevation={2} className="p-1 h-full">
              <MessagesSection prompt={prompt} />
            </Paper>
          </div>
          <ResizableSplitter onResize={handleResize} minTopRatio={0.3} minBottomRatio={0.3} />
          <div
            className="flex-shrink-0"
            style={{
              flexBasis: `${(1 - messagesHeightRatio) * 100}%`,
              minHeight: "30%",
            }}
          >
            <Paper elevation={2} className="p-1 h-full">
              <OutputField
                promptId={prompt.id}
                running={prompt.running || false}
                runResponse={prompt.runResponse}
                responseFormat={prompt.responseFormat}
                dialogOpen={responseSchemaDialogOpen}
                onCloseDialog={() => setResponseSchemaDialogOpen(false)}
              />
            </Paper>
          </div>
        </div>
      </Container>
      <SavePromptDialog open={savePromptOpen} setOpen={setSavePromptOpen} prompt={prompt} initialName={nameInputValue} />
      <ToolsDialog open={toolsDialogOpen} setOpen={setToolsDialogOpen} prompt={prompt} />
      <Snackbar {...snackbarProps}>
        <Alert {...alertProps} />
      </Snackbar>
    </div>
  );
};

export default Prompt;
