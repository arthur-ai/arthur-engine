import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DefaultModelCard } from "./default-model-card";

import { ModelProvider } from "@/lib/api-client/api-client";

const refetchAvailableModels = vi.fn();
const availableModels = vi.fn();

vi.mock("notistack", () => ({ useSnackbar: () => ({ enqueueSnackbar: vi.fn() }) }));
vi.mock("@/hooks/useModelProviders", () => ({ useAvailableModels: () => availableModels() }));
vi.mock("../hooks/useDefaultModelProvider", () => ({
  useDefaultModelProvider: () => ({ data: { provider: "openai", model_name: null }, isLoading: false, isError: false, refetch: vi.fn() }),
  useSetDefaultModelProvider: () => ({ isPending: false, mutateAsync: vi.fn() }),
  useClearDefaultModelProvider: () => ({ isPending: false, mutateAsync: vi.fn() }),
}));

// Auto-cleanup only registers under vitest `globals: true`, which this project does not set.
afterEach(cleanup);

const renderCard = () => render(<DefaultModelCard enabledProviders={["openai" as ModelProvider]} getProviderDisplayName={() => "OpenAI"} />);

describe("DefaultModelCard", () => {
  it("says the model list failed to load and retries it", () => {
    availableModels.mockReturnValue({ availableModels: new Map(), failedProviders: ["openai"], refetchAvailableModels });
    renderCard();

    expect(screen.getByText("Couldn't load the models for OpenAI.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(refetchAvailableModels).toHaveBeenCalled();
  });

  it("shows no failure when the model list loaded", () => {
    availableModels.mockReturnValue({ availableModels: new Map([["openai", ["gpt-4.1-mini"]]]), failedProviders: [], refetchAvailableModels });
    renderCard();

    expect(screen.queryByText(/Couldn't load the models/)).toBeNull();
  });
});
