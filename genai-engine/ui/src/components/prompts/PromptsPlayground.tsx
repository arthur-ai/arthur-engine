import React, { useCallback, useReducer } from "react";
import Collapse from "@mui/material/Collapse";
import PromptComponent from "./PromptComponent";
import Container from "@mui/material/Container";
import Paper from "@mui/material/Paper";
import Button from "@mui/material/Button";
import { promptsReducer, initialState } from "./reducer";

const PromptsPlayground = () => {
  const [state, dispatch] = useReducer(promptsReducer, initialState);

  const handleAddPrompt = useCallback(() => {
    dispatch({ type: "addPrompt" });
  }, [dispatch]);

  return (
    <div className="h-screen bg-gray-300">
      <div className={`h-full w-full p-1 flex flex-col gap-1`}>
        <div className={`bg-gray-400 flex-shrink-0 p-1`}>
          <div className="flex justify-between items-center">
            <div>HEADER</div>
            <Button variant="contained" onClick={handleAddPrompt}>
              Add Prompt
            </Button>
          </div>
          <Container component="div" maxWidth="xl" disableGutters>
            <Paper elevation={3} className="p-1">
              <Collapse in={state.keywords.size > 0}>
                <div>KEYWORDS</div>
                {Array.from(state.keywords.keys()).map((keyword) => (
                  <div key={keyword}>{keyword}</div>
                ))}
              </Collapse>
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
