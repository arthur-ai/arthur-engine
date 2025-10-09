import AttachMoneyIcon from "@mui/icons-material/AttachMoney";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import GeneratingTokensIcon from "@mui/icons-material/GeneratingTokens"; // Probably change in future
import HourglassEmptyIcon from "@mui/icons-material/HourglassEmpty";
import Collapse from "@mui/material/Collapse";
import Divider from "@mui/material/Divider";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import React, { useState } from "react";

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

const OutputField = () => {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleExpand = () => {
    setIsExpanded((prev) => !prev);
  };

  return (
    <div>
      <div onClick={handleExpand} className="flex items-center cursor-pointer">
        <span>Output</span>
        {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
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
            <Tooltip title="Latency in Seconds">
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
    </div>
  );
};

export default OutputField;
