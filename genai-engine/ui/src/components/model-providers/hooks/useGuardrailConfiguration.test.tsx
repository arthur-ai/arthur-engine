import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";

import { useGuardrailCatalog, useGuardrailConfiguration } from "./useGuardrailConfiguration";
import { useRemoveProvider } from "./useRemoveProvider";
import { useSaveProvider } from "./useSaveProvider";

const api = vi.hoisted(() => ({
  getConfigurationApiV2ConfigurationGet: vi.fn(),
  getModelProviderWhitelistApiV1ModelProvidersProviderModelWhitelistGet: vi.fn(),
  setModelProviderApiV1ModelProvidersProviderPut: vi.fn(),
  deleteModelProviderApiV1ModelProvidersProviderDelete: vi.fn(),
}));

vi.mock("@/hooks/useApi", () => ({ useApi: () => ({ api }) }));
vi.mock("@/contexts/AuthContext", () => ({ useAuth: () => ({ me: { roles: ["ORG-ADMIN"] } }) }));

afterEach(cleanup);

it("refreshes the guardrail catalog and missing-provider status after credential rotation and deletion", async () => {
  let enabled = true;
  let catalogModel = "old-model";
  api.getConfigurationApiV2ConfigurationGet.mockImplementation(async () => ({
    data: {
      guardrail_llm: { provider: "openai", model: "judge-alias" },
      guardrail_llm_status: enabled ? "configured" : "needs_configuration",
    },
  }));
  api.getModelProviderWhitelistApiV1ModelProvidersProviderModelWhitelistGet.mockImplementation(async () => ({
    data: { catalog: enabled ? [catalogModel] : [] },
  }));
  api.setModelProviderApiV1ModelProvidersProviderPut.mockImplementation(async () => {
    catalogModel = "rotated-model";
    return { data: { provider: "openai", enabled: true } };
  });
  api.deleteModelProviderApiV1ModelProvidersProviderDelete.mockImplementation(async () => {
    enabled = false;
    return { data: {} };
  });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  const { result } = renderHook(
    () => ({
      catalog: useGuardrailCatalog("openai", true),
      configuration: useGuardrailConfiguration(),
      save: useSaveProvider(),
      remove: useRemoveProvider(),
    }),
    { wrapper }
  );
  await waitFor(() => expect(result.current.catalog.data?.catalog).toEqual(["old-model"]));
  await act(async () => {
    await result.current.save.mutateAsync({
      provider: { provider: "openai", enabled: true },
      data: { api_key: "rotated-test-credential" },
    });
  });
  await waitFor(() => expect(result.current.catalog.data?.catalog).toEqual(["rotated-model"]));
  await act(async () => {
    await result.current.remove.mutateAsync("openai");
  });
  await waitFor(() => expect(result.current.catalog.data?.catalog).toEqual([]));
  await waitFor(() => expect(result.current.configuration.data?.guardrail_llm_status).toBe("needs_configuration"));
  expect(result.current.configuration.data?.guardrail_llm?.model).toBe("judge-alias");
  queryClient.clear();
});
