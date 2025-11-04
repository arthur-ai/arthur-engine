import Divider from "@mui/material/Divider";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import React from "react";

import { usePromptContext } from "./PromptsPlaygroundContext";

const VariableInputs = () => {
  const { state, dispatch } = usePromptContext();

  const handleKeywordValueChange = (keyword: string, value: string) => {
    dispatch({ type: "updateKeywordValue", payload: { keyword, value } });
  };

  const variables = Array.from(state.keywords.keys());

  return (
    <Paper elevation={0} className="h-full p-2 overflow-y-auto">
      <Typography variant="h5" className="text-center mb-2">
        Variables
      </Typography>
      <Typography variant="body2" className="text-center mb-2">
        Variables allow you to create reusable templates by using double curly (mustache) braces like <code>{`{{variable}}`}</code>. When you define a
        variable below, it will automatically replace all instances of <code>{`{{variable}}`}</code> in your prompt messages. This lets you quickly
        test different values without editing each message individually.
      </Typography>
      <Divider className="my-2" />
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
    </Paper>
  );
};

export default VariableInputs;
