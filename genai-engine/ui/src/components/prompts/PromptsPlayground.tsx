import React, { useCallback, useReducer } from "react";
import PromptComponent from "./PromptComponent";
import Container from "@mui/material/Container";
import Paper from "@mui/material/Paper";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import { promptsReducer, initialState } from "./reducer";
import Typography from "@mui/material/Typography";
import Divider from "@mui/material/Divider";

const PromptsPlayground = () => {
  const [state, dispatch] = useReducer(promptsReducer, initialState);

  const handleAddPrompt = useCallback(() => {
    dispatch({ type: "addPrompt" });
  }, [dispatch]);

  const handleKeywordValueChange = useCallback(
    (keyword: string, value: string) => {
      dispatch({ type: "updateKeywordValue", payload: { keyword, value } });
    },
    [dispatch]
  );

  const keywords = Array.from(state.keywords.keys());

  return (
    <div className="h-screen bg-gray-300">
      <div className={`h-full w-full p-1 flex flex-col gap-1`}>
        <div className={`bg-gray-400 flex-shrink-0 p-1`}>
          <div className="flex justify-around items-center mb-1">
            <div>Prompts Playground</div>
            <Button variant="contained" size="small" onClick={handleAddPrompt}>
              Add Prompt
            </Button>
            <Button variant="contained" size="small" onClick={() => {}}>
              Output Schemas
            </Button>
            <Button variant="contained" size="small" onClick={() => {}}>
              Tools
            </Button>
          </div>
          <Container component="div" maxWidth="xl" disableGutters>
            <Paper elevation={3} className="p-1">
              <div className="grid grid-template-rows-2">
                <div className="flex justify-center items-center">
                  <Typography variant="h5">Keyword Templates</Typography>
                </div>
                <div className="flex justify-center items-center">
                  <Typography variant="body2">
                    Keywords are identified by mustache braces &#123;&#123;keyword&#125;&#125; and
                    are used to replace values in the messages. You can use the
                    same keyword in multiple prompts/messages.
                  </Typography>
                </div>
              </div>
              <Divider />
              <div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-1">
                {keywords.map((keyword) => (
                  <div key={keyword} className="w-full">
                    <TextField
                      id={`keyword-${keyword}`}
                      label={keyword}
                      value={state.keywords.get(keyword)}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                        handleKeywordValueChange(keyword, e.target.value);
                      }}
                      variant="standard"
                      fullWidth
                    />
                  </div>
                ))}
              </div>
            </Paper>
          </Container>
        </div>
        <div className="flex-1 overflow-y-auto min-h-0">
          <div className="grid grid-cols-[repeat(auto-fit,minmax(500px,1fr))] gap-1 min-h-full">
            {state.prompts.map((prompt) => (
              <PromptComponent
                key={prompt.id}
                prompt={prompt}
                dispatch={dispatch}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PromptsPlayground;
