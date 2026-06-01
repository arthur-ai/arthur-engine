import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { PromptType } from "../types";

import ManagementButtons from "./ManagementButtons";

import { TOUR_IDS } from "@/features/task-tour/selectors";

vi.mock("../PromptsPlaygroundContext", () => ({
  usePromptContext: () => ({
    dispatch: vi.fn(),
    state: { keywords: new Map() },
    experimentConfig: null,
    handleRunSingleWithConfig: null,
    isRunningExperiment: false,
  }),
}));

vi.mock("./ModelParamsDialog", () => ({
  default: () => null,
}));

vi.mock("./PreviewPromptModal", () => ({
  default: () => null,
}));

vi.mock("@/services/amplitude", () => ({
  EVENT_NAMES: {
    PROMPT_PREVIEW: "prompt_preview",
    PROMPT_RUN: "prompt_run",
  },
  track: vi.fn(),
}));

function promptFixture(): PromptType {
  return {
    id: "prompt-id",
    classification: "default",
    name: "demo_task_prompt",
    created_at: undefined,
    modelName: "gpt-4",
    modelProvider: "openai",
    messages: [],
    modelParameters: {},
    runResponse: null,
    responseFormat: undefined,
    tools: [],
    running: false,
    version: 1,
    savedSnapshot: "{}",
  };
}

describe("ManagementButtons", () => {
  it("marks the Duplicate Prompt button as the prompt playground duplicate tour target", () => {
    render(<ManagementButtons prompt={promptFixture()} setSavePromptOpen={vi.fn()} />);

    expect(screen.getByRole("button", { name: /duplicate/i }).getAttribute("data-tour-id")).toBe(TOUR_IDS.playgroundDuplicatePrompt);
  });
});
