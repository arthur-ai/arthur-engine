import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it } from "vitest";

import { ChatMessage } from "./ChatMessage";

import { isDefaultModelNotSetError } from "@/lib/api-errors";

afterEach(cleanup);

describe("ChatMessage", () => {
  it("offers the Model Providers page when no default model is set", () => {
    render(
      <MemoryRouter initialEntries={["/tasks/t1"]}>
        <Routes>
          <Route
            path="/tasks/t1"
            element={<ChatMessage message={{ role: "assistant", content: "The AI Assistant needs a default model.", action: "set_default_model" }} />}
          />
          <Route path="/settings/model-providers" element={<div>Model Providers page</div>} />
        </Routes>
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole("button", { name: "Open Model Providers" }));
    expect(screen.getByText("Model Providers page")).toBeTruthy();
  });

  it("shows no button on an ordinary answer", () => {
    render(
      <MemoryRouter>
        <ChatMessage message={{ role: "assistant", content: "Here are your tasks." }} />
      </MemoryRouter>
    );
    expect(screen.queryByRole("button", { name: "Open Model Providers" })).toBeNull();
  });
});

describe("isDefaultModelNotSetError", () => {
  it("matches only the engine's no-default 400", () => {
    const detail = { detail: "No default model provider is set. Set one on the Model Providers page." };
    expect(isDefaultModelNotSetError(400, detail)).toBe(true);
    expect(isDefaultModelNotSetError(500, detail)).toBe(false);
    expect(isDefaultModelNotSetError(400, { detail: "model provider anthropic is not configured" })).toBe(false);
    expect(isDefaultModelNotSetError(400, { detail: { error_code: "X" } })).toBe(false);
  });
});
