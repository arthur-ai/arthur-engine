import { ModelProvider, ModelProviderResponse, ModelProviderWhitelist, PutModelProviderCredentials } from "@/lib/api-client/api-client";

// DEMO ONLY. The engine can't serve ScaleDown until litellm ships its provider
// (BerriAI/litellm#44168) and arthur-common adds the enum value (arthur-common#228),
// so the model-provider hooks answer ScaleDown requests from this browser-local store
// instead of the API. Delete this file and its call sites once the backend supports it.

export const SCALEDOWN: ModelProvider = "scaledown";

const CATALOG = ["compress", "summarize", "extract", "classify", "decisions"];

const STORAGE_KEY = "arthur.demo.scaledown-provider";

type DemoState = {
  enabled: boolean;
  whitelist: string[] | null;
};

const DEFAULT_STATE: DemoState = { enabled: false, whitelist: null };

const read = (): DemoState => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULT_STATE, ...JSON.parse(raw) } : DEFAULT_STATE;
  } catch {
    return DEFAULT_STATE;
  }
};

const write = (state: DemoState) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Storage unavailable: the demo state just won't survive a reload.
  }
};

// Mimics network latency so save/delete spinners show like they do for real providers.
const settle = () => new Promise((resolve) => setTimeout(resolve, 400));

export const getScaleDownProvider = (): ModelProviderResponse => ({
  provider: SCALEDOWN,
  enabled: read().enabled,
});

export const saveScaleDownCredentials = async (data: PutModelProviderCredentials): Promise<ModelProviderResponse> => {
  await settle();
  if (!data.api_key) {
    throw new Error("API Key is required");
  }
  write({ ...read(), enabled: true });
  return getScaleDownProvider();
};

export const removeScaleDown = async () => {
  await settle();
  write({ ...read(), enabled: false });
};

export const getScaleDownWhitelist = (): ModelProviderWhitelist => ({
  provider: SCALEDOWN,
  catalog: CATALOG,
  whitelist: read().whitelist,
});

export const setScaleDownWhitelist = async (models: string[] | null) => {
  await settle();
  write({ ...read(), whitelist: models });
};
