import Editor from "@monaco-editor/react";
import AttachMoneyIcon from "@mui/icons-material/AttachMoney";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import DataObjectIcon from "@mui/icons-material/DataObject";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import GeneratingTokensIcon from "@mui/icons-material/GeneratingTokens"; // Probably change in future
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import Button from "@mui/material/Button";
import Collapse from "@mui/material/Collapse";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Divider from "@mui/material/Divider";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import React, { useState } from "react";

import { OutputFieldProps } from "./types";

const OUTPUT_TEXT = "I'm an llm response";
const SAMPLE_RESPONSE_OBJECT = {
  data: {
    span: {
      __typename: "Span",
      id: "U3BhbjoxNTA1",
      spanId: "2cc4e1e2c004999",
      trace: {
        id: "VHJhY2U6MTA1",
        traceId: "5ab12d0c810d1a193623a8a2c20fab62",
        project: {
          id: "UHJvamVjdDoz",
        },
      },
      tokenCountTotal: 24,
      latencyMs: 1819.7,
      costSummary: {
        total: {
          cost: 0.0001275,
        },
      },
    },
  },
};

const DEFAULT_RESPONSE_FORMAT = JSON.stringify(
  {
    type: "json_schema",
    schema: {},
  },
  null,
  2
);

const OutputField = ({
  promptId,
  responseFormat,
  dispatch,
}: OutputFieldProps) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [copiedFormat, setCopiedFormat] = useState<string | undefined>(
    responseFormat || DEFAULT_RESPONSE_FORMAT
  );

  const handleExpand = () => {
    setIsExpanded((prev) => !prev);
  };

  const handleOpen = (e: React.MouseEvent<SVGSVGElement>) => {
    e.stopPropagation();
    setIsOpen(true);
  };

  const handleClose = () => {
    setIsOpen(false);
  };

  const handleCancel = () => {
    handleClose();
    setCopiedFormat(responseFormat);
  };

  const handleChange = (value: string) => {
    setCopiedFormat(value);
  };

  const handleSave = () => {
    handleClose();
    dispatch({
      type: "updateResponseFormat",
      payload: { promptId, responseFormat: copiedFormat },
    });
  };

  return (
    <>
      <div
        onClick={handleExpand}
        className="flex justify-between cursor-pointer"
      >
        <div className="flex items-center">
          {isExpanded ? <ExpandMoreIcon /> : <ChevronRightIcon />}
          <span>Output</span>
        </div>
        <div className="flex items-center">
          <Tooltip title="Format Output">
            <DataObjectIcon
              aria-label="open"
              onClick={(e) => handleOpen(e)}
            ></DataObjectIcon>
          </Tooltip>
        </div>
      </div>
      <Collapse in={isExpanded}>
        <div>{OUTPUT_TEXT}</div>
        <Divider />
        <div className="flex gap-3">
          <div className="flex items-center">
            <Tooltip title="Total Tokens">
              <GeneratingTokensIcon />
            </Tooltip>
            <Typography variant="body1">
              {SAMPLE_RESPONSE_OBJECT.data.span.tokenCountTotal}
            </Typography>
          </div>
          <div className="flex items-center">
            <Tooltip title="Latency (seconds)">
              <HourglassEmptyIcon />
            </Tooltip>
            <Typography variant="body1">
              {(SAMPLE_RESPONSE_OBJECT.data.span.latencyMs / 1000).toFixed(2)}
            </Typography>
          </div>
          <div className="flex items-center">
            <Tooltip title="Cost">
              <AttachMoneyIcon />
            </Tooltip>
            <Typography variant="body1">
              {SAMPLE_RESPONSE_OBJECT.data.span.costSummary.total.cost}
            </Typography>
          </div>
        </div>
      </Collapse>
      <Dialog open={isOpen} onClose={handleClose} fullWidth>
        <DialogTitle>Format Response Output</DialogTitle>
        <DialogContent>
          <div style={{ height: "300px", width: "100%" }}>
            <Editor
              height="300px"
              defaultLanguage="json"
              theme="light"
              value={copiedFormat}
              onChange={(value) => {
                if (value) {
                  handleChange(value);
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
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancel}>Cancel</Button>
          <Button onClick={handleSave}>Save</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default OutputField;
