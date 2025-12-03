import Editor from "@monaco-editor/react";
import AttachMoneyIcon from "@mui/icons-material/AttachMoney";
import GeneratingTokensIcon from "@mui/icons-material/GeneratingTokens"; // Probably change in future
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import Skeleton from "@mui/material/Skeleton";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import React, { useCallback, useEffect, useState } from "react";

import { usePromptContext } from "../PromptsPlaygroundContext";
import { OutputFieldProps } from "../types";

const DEFAULT_RESPONSE_FORMAT = JSON.stringify(
  {
    "type": "json_schema",
    "json_schema": {
      "name": "schema_name_here",
      "description": "description of the response schema",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "field1": {
            "type": "string",
            "description": "Describe what this string should contain"
          },
          "field2": {
            "type": "number",
            "description": "Describe what this number represents"
          },
          "field3": {
            "type": "boolean",
            "description": "Explain what true/false means in this context"
          }
        },
        "required": ["field1", "field2"],
        "additionalProperties": false
      }
    }
  },
  null,
  2
);

const getFormatValue = (format: string | undefined) => {
  return format !== undefined ? format : DEFAULT_RESPONSE_FORMAT;
};

const skeletons = () => (
  <>
    <Skeleton variant="text" width="92%" />
    <Skeleton variant="text" width="99%" />
    <Skeleton variant="text" width="96%" />
    <Skeleton variant="text" width="99%" />
    <Skeleton variant="text" width="80%" />
  </>
);

const OutputField = ({ promptId, running, runResponse, responseFormat, dialogOpen, onCloseDialog }: OutputFieldProps) => {
  const { dispatch } = usePromptContext();
  const [isPopoutOpen, setIsPopoutOpen] = useState(false);
  const [copiedFormat, setCopiedFormat] = useState<string | undefined>(getFormatValue(responseFormat));

  const handleOpen = useCallback(() => {
    // Store the current value before opening
    setCopiedFormat(getFormatValue(responseFormat));
  }, [responseFormat]);

  const handleClose = () => {
    onCloseDialog();
  };

  const handlePopoutOpen = () => {
    setIsPopoutOpen(true);
  };

  const handlePopoutClose = () => {
    setIsPopoutOpen(false);
  };

  const handleCancel = () => {
    handleClose();
    setCopiedFormat(getFormatValue(responseFormat));
  };

  const handleChange = (value: string) => {
    setCopiedFormat(value);
  };

  useEffect(() => {
    setCopiedFormat(getFormatValue(responseFormat));
  }, [responseFormat]);

  const handleSave = () => {
    handleClose();
    dispatch({
      type: "updateResponseFormat",
      payload: { promptId, responseFormat: copiedFormat },
    });
  };

  useEffect(() => {
    if (dialogOpen) {
      handleOpen();
    }
  }, [dialogOpen, handleOpen]);

  const renderContent = (
    <>
      {runResponse?.content && <div style={{ whiteSpace: "pre-wrap" }}>{runResponse.content}</div>}
      {runResponse?.tool_calls && runResponse.tool_calls.length > 0 && (
        <>
          {runResponse?.content && <Divider />}
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            Tool Calls
          </Typography>
          <div style={{ height: "300px", width: "100%" }}>
            <Editor
              height="300px"
              defaultLanguage="json"
              theme="light"
              value={JSON.stringify(runResponse.tool_calls, null, 2)}
              options={{
                readOnly: true,
                minimap: { enabled: false },
                lineNumbers: "on",
                fontSize: 12,
                tabSize: 2,
                automaticLayout: true,
              }}
            />
          </div>
        </>
      )}
    </>
  );

  const showSkeletons = running && !runResponse?.content;

  return (
    <>
      <div className="flex flex-col h-full">
        <div className="flex justify-between">
          <div className="flex items-center">
            <span>
              <Typography variant="body1">Response</Typography>
            </span>
          </div>
          <div className="flex items-center">
            <Tooltip title="Popout Response">
              <IconButton aria-label="popout_response" onClick={handlePopoutOpen} size="small">
                <OpenInNewIcon color="primary" />
              </IconButton>
            </Tooltip>
          </div>
        </div>
        <Divider />
        <div className="flex-1 overflow-y-auto" style={{ minHeight: 0 }}>
          {showSkeletons ? <>{skeletons()}</> : <div className="flex flex-col h-full">{renderContent}</div>}
        </div>
        <Divider />
        <div className="flex gap-3 shrink-0">
          {/* eslint-disable-next-line no-constant-condition */}
          {false ? (
            <div className="flex items-center">
              <Tooltip title="Total Tokens">
                <GeneratingTokensIcon />
              </Tooltip>
              <Typography variant="body1">{/* {SAMPLE_RESPONSE_OBJECT.data.span.tokenCountTotal} */}</Typography>
            </div>
          ) : null}
          {/* eslint-disable-next-line no-constant-condition */}
          {false ? (
            <div className="flex items-center">
              <Tooltip title="Latency (seconds)">
                <HourglassEmptyIcon />
              </Tooltip>
              <Typography variant="body1">{/* {(latencyMs / 1000).toFixed(2)} */}</Typography>
            </div>
          ) : null}
          <div className="flex items-center">
            <Tooltip title="Cost">
              <AttachMoneyIcon />
            </Tooltip>
            <Typography variant="body1">{running ? <Skeleton variant="text" width="100px" /> : runResponse?.cost || "-"}</Typography>
          </div>
        </div>
      </div>
      <Dialog open={dialogOpen} onClose={onCloseDialog} fullWidth>
        <DialogTitle>Format Response Output</DialogTitle>
        <DialogContent>
          <div style={{ height: "300px", width: "100%" }}>
            <Editor
              height="300px"
              defaultLanguage="json"
              theme="light"
              value={copiedFormat}
              onChange={(value) => {
                handleChange(value || "");
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
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancel}>Cancel</Button>
          <Button onClick={handleSave}>Save</Button>
        </DialogActions>
      </Dialog>
      <Dialog open={isPopoutOpen} onClose={handlePopoutClose} fullWidth maxWidth="md">
        <DialogTitle>
          <Typography variant="h6">Response</Typography>
        </DialogTitle>
        <DialogContent>
          <div style={{ minHeight: "200px", maxHeight: "70vh", overflowY: "auto" }}>
            {showSkeletons ? (
              <div className="flex flex-col items-center justify-center h-full">{skeletons()}</div>
            ) : (
              <div className="flex flex-col" style={{ gap: "16px" }}>
                {renderContent}
                {!runResponse?.content && !runResponse?.tool_calls && <div>No response yet</div>}
              </div>
            )}
          </div>
        </DialogContent>
        <DialogActions>
          <Button onClick={handlePopoutClose}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default OutputField;
