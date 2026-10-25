import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ModelSettingsTabs } from "../ModelSettingsTabs";

import { GuardrailSettings } from "./index";

const mocks = vi.hoisted(() => ({
  permissions: { canRead: true, canWrite: true },
  configuration: vi.fn(),
  providers: vi.fn(),
  catalog: vi.fn(),
  mutate: vi.fn(),
  refetch: vi.fn(),
  snackbar: vi.fn(),
}));

vi.mock("@/components/model-providers/hooks/useGuardrailConfiguration", () => ({
  useGuardrailPermissions: () => mocks.permissions,
  useGuardrailConfiguration: mocks.configuration,
  useGuardrailCatalog: mocks.catalog,
  useSaveGuardrailConfiguration: () => ({ mutateAsync: mocks.mutate, isPending: false }),
}));
vi.mock("@/components/model-providers/hooks/useProviders", () => ({ useProviders: mocks.providers }));
vi.mock("notistack", () => ({ useSnackbar: () => ({ enqueueSnackbar: mocks.snackbar }) }));

afterEach(cleanup);
beforeEach(() => {
  vi.clearAllMocks();
  mocks.permissions = { canRead: true, canWrite: true };
  mocks.configuration.mockReturnValue({
    data: { guardrail_llm: { provider: "openai", model: "gpt-4o", base_model: null }, guardrail_llm_status: "configured" },
    refetch: mocks.refetch,
  });

  mocks.providers.mockReturnValue({ data: [{ provider: "openai", enabled: true, supports_custom_models: true }] });
  mocks.catalog.mockReturnValue({ data: { catalog: ["gpt-4o", "catalog-only-model"] } });
  mocks.mutate.mockResolvedValue({});
  mocks.refetch.mockResolvedValue({ isError: false });
});

describe("Guardrail Settings", () => {
  it("can clear saved optional metadata and save an exact alias when the catalog fails", async () => {
    mocks.configuration.mockReturnValue({
      data: { guardrail_llm: { provider: "openai", model: "team/old/alias", base_model: "gpt-4o" }, guardrail_llm_status: "configured" },
      refetch: mocks.refetch,
    });
    mocks.catalog.mockReturnValue({ isError: true, refetch: vi.fn() });
    render(<GuardrailSettings />);
    const metadata = screen.getByLabelText("Catalog base model (optional)");
    fireEvent.focus(metadata);
    fireEvent.click(within(metadata.closest(".MuiAutocomplete-root") as HTMLElement).getByRole("button", { name: "Clear" }));
    fireEvent.change(screen.getByLabelText("Model or exact routing name"), { target: { value: "team/new/exact-alias" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(mocks.mutate).toHaveBeenCalledWith({ provider: "openai", model: "team/new/exact-alias", base_model: null }));
  });
  it("does not mount configuration queries for unauthorized readers", () => {
    mocks.permissions = { canRead: false, canWrite: false };
    render(<GuardrailSettings />);
    expect(mocks.configuration).not.toHaveBeenCalled();
    expect(mocks.providers).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Save" })).toBeNull();
  });

  it("shows the global scope and a read-only auditor editor", () => {
    mocks.permissions.canWrite = false;
    render(<GuardrailSettings />);
    expect(screen.getByText(/all organizations/)).toBeTruthy();
    expect(screen.getByLabelText("Model provider").getAttribute("aria-disabled")).toBe("true");
    expect(screen.queryByRole("button", { name: "Save" })).toBeNull();
    expect(screen.queryByText(/legacy|fallback|disable guardrails/i)).toBeNull();
  });

  it("allows exact proxy aliases when the catalog fails and retains a rejected draft", async () => {
    mocks.catalog.mockReturnValue({ isError: true, refetch: vi.fn() });
    mocks.mutate.mockRejectedValue(new Error("private upstream detail"));
    render(<GuardrailSettings />);
    const model = screen.getByLabelText("Model or exact routing name");
    fireEvent.change(model, { target: { value: "team/exact/alias" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(screen.getByText(/Guardrail settings could not be saved/)).toBeTruthy());
    expect((model as HTMLInputElement).value).toBe("team/exact/alias");
    expect(mocks.mutate).toHaveBeenCalledWith({ provider: "openai", model: "team/exact/alias", base_model: null });
    expect(mocks.snackbar).not.toHaveBeenCalled();
    expect(screen.queryByText(/private upstream detail/)).toBeNull();
  });

  it("shows success only after save and refetch complete", async () => {
    render(<GuardrailSettings />);
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(mocks.snackbar).toHaveBeenCalledWith("Guardrail settings saved", { variant: "success" }));
    expect(mocks.refetch).toHaveBeenCalledOnce();
    expect(mocks.mutate).toHaveBeenCalledWith({ provider: "openai", model: "gpt-4o", base_model: null });
  });

  it("shows a load error with retry and no editor", () => {
    mocks.configuration.mockReturnValue({ isError: true, refetch: mocks.refetch });
    mocks.providers.mockReturnValue({ data: [], refetch: vi.fn() });
    render(<GuardrailSettings />);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(mocks.refetch).toHaveBeenCalledOnce();
    expect(screen.queryByRole("button", { name: "Save" })).toBeNull();
  });

  it("shows loading before rendering the form", () => {
    mocks.configuration.mockReturnValue({ isLoading: true });
    render(<GuardrailSettings />);
    expect(screen.getByLabelText("Loading guardrail settings")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Save" })).toBeNull();
  });

  it("retains a disabled provider selection and requires configuration", () => {
    mocks.configuration.mockReturnValue({
      data: { guardrail_llm: { provider: "openai", model: "gpt-4o" }, guardrail_llm_status: "needs_configuration" },
    });
    mocks.providers.mockReturnValue({ data: [{ provider: "openai", enabled: false }] });
    render(<GuardrailSettings />);
    expect(screen.getByText("A model provider and model must be configured for guardrails.")).toBeTruthy();
    expect((screen.getByRole("button", { name: "Save" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("openai (not configured)")).toBeTruthy();
  });

  it("renders sibling tabs without adding them to API Keys", () => {
    const view = render(
      <MemoryRouter initialEntries={["/settings/guardrails"]}>
        <ModelSettingsTabs />
      </MemoryRouter>
    );
    expect(screen.getByRole("tab", { name: "Model Providers" }).getAttribute("href")).toBe("/settings/model-providers");
    expect(screen.getByRole("tab", { name: "Guardrail Settings" }).getAttribute("aria-selected")).toBe("true");
    view.unmount();
    render(
      <MemoryRouter initialEntries={["/settings/api-keys"]}>
        <ModelSettingsTabs />
      </MemoryRouter>
    );
    expect(screen.queryByRole("tab")).toBeNull();
  });
});
