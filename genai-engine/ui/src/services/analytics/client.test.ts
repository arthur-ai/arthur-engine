import { beforeEach, describe, expect, it, vi } from "vitest";

const amplitudeMock = vi.hoisted(() => ({
  init: vi.fn(),
  track: vi.fn(),
  add: vi.fn(),
  setUserId: vi.fn(),
  identify: vi.fn(),
  Identify: vi.fn(() => ({ set: vi.fn() })),
  Types: { LogLevel: { None: 0, Error: 1, Warn: 2, Verbose: 3, Debug: 4 } },
}));

// Debug logging is off unless VITE_AMPLITUDE_DEBUG is set, so the default is Warn.
const expectedLogLevel = amplitudeMock.Types.LogLevel.Warn;

const sessionReplayPluginMock = vi.hoisted(() => vi.fn(() => ({ name: "session-replay-mock" })));

vi.mock("@amplitude/analytics-browser", () => amplitudeMock);
vi.mock("@amplitude/plugin-session-replay-browser", () => ({
  sessionReplayPlugin: sessionReplayPluginMock,
}));

async function importClient() {
  vi.resetModules();
  return import("./client");
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.unstubAllEnvs();
});

describe("initAnalytics", () => {
  it("does not init the SDK when VITE_AMPLITUDE_TOKEN is missing", async () => {
    vi.stubEnv("VITE_AMPLITUDE_TOKEN", "");
    const { initAnalytics } = await importClient();
    initAnalytics();
    expect(amplitudeMock.init).not.toHaveBeenCalled();
  });

  it("inits without the replay plugin when no sample rate is set", async () => {
    vi.stubEnv("VITE_AMPLITUDE_TOKEN", "test-key");
    vi.stubEnv("VITE_AMPLITUDE_REPLAY_SAMPLE_RATE", "");
    const { initAnalytics } = await importClient();
    initAnalytics();
    expect(amplitudeMock.add).not.toHaveBeenCalled();
    expect(amplitudeMock.init).toHaveBeenCalledWith("test-key", {
      defaultTracking: false,
      serverZone: "US",
      logLevel: expectedLogLevel,
    });
  });

  it("uses debug logLevel when VITE_AMPLITUDE_DEBUG is set", async () => {
    vi.stubEnv("VITE_AMPLITUDE_TOKEN", "test-key");
    vi.stubEnv("VITE_AMPLITUDE_REPLAY_SAMPLE_RATE", "");
    vi.stubEnv("VITE_AMPLITUDE_DEBUG", "true");
    const { initAnalytics } = await importClient();
    initAnalytics();
    expect(amplitudeMock.init).toHaveBeenCalledWith("test-key", expect.objectContaining({ logLevel: amplitudeMock.Types.LogLevel.Debug }));
  });

  it("registers the replay plugin before init when a sample rate is set", async () => {
    vi.stubEnv("VITE_AMPLITUDE_TOKEN", "test-key");
    vi.stubEnv("VITE_AMPLITUDE_REPLAY_SAMPLE_RATE", "0.5");
    const { initAnalytics } = await importClient();
    initAnalytics();
    expect(amplitudeMock.add).toHaveBeenCalledWith({ name: "session-replay-mock" });
    const addOrder = amplitudeMock.add.mock.invocationCallOrder[0];
    const initOrder = amplitudeMock.init.mock.invocationCallOrder[0];
    expect(addOrder).toBeLessThan(initOrder);
  });

  it("initializes the SDK at most once across repeated calls", async () => {
    // Re-initializing the Browser SDK reassigns the device ID after Session
    // Replay has locked onto the first one, which Amplitude documents as the
    // cause of event<->replay device ID mismatches. initAnalytics must be
    // idempotent.
    vi.stubEnv("VITE_AMPLITUDE_TOKEN", "test-key");
    vi.stubEnv("VITE_AMPLITUDE_REPLAY_SAMPLE_RATE", "0.5");
    const { initAnalytics } = await importClient();
    initAnalytics();
    initAnalytics();
    expect(amplitudeMock.init).toHaveBeenCalledTimes(1);
    expect(amplitudeMock.add).toHaveBeenCalledTimes(1);
  });
});

describe("track", () => {
  it("no-ops when analytics is not initialized", async () => {
    const { track } = await importClient();
    track("dataset/save_version", { dataset_id: "d1" });
    expect(amplitudeMock.track).not.toHaveBeenCalled();
  });

  it("forwards event name and properties after init", async () => {
    vi.stubEnv("VITE_AMPLITUDE_TOKEN", "test-key");
    const { initAnalytics, track } = await importClient();
    initAnalytics();
    track("dataset/save_version", { dataset_id: "d1" });
    expect(amplitudeMock.track).toHaveBeenCalledWith("dataset/save_version", { dataset_id: "d1" });
  });

  it("accepts property-less events with no second argument", async () => {
    vi.stubEnv("VITE_AMPLITUDE_TOKEN", "test-key");
    const { initAnalytics, track } = await importClient();
    initAnalytics();
    track("onboarding/landing_viewed");
    expect(amplitudeMock.track).toHaveBeenCalledWith("onboarding/landing_viewed", undefined);
  });
});

describe("trackDynamic", () => {
  it("forwards arbitrary event names after init", async () => {
    vi.stubEnv("VITE_AMPLITUDE_TOKEN", "test-key");
    const { initAnalytics, trackDynamic } = await importClient();
    initAnalytics();
    trackDynamic("task-tour.step:enter", { stepId: "s1" });
    expect(amplitudeMock.track).toHaveBeenCalledWith("task-tour.step:enter", { stepId: "s1" });
  });
});

describe("clearUser", () => {
  it("clears the user id after init", async () => {
    vi.stubEnv("VITE_AMPLITUDE_TOKEN", "test-key");
    const { initAnalytics, clearUser } = await importClient();
    initAnalytics();
    clearUser();
    expect(amplitudeMock.setUserId).toHaveBeenCalledWith(undefined);
  });
});
