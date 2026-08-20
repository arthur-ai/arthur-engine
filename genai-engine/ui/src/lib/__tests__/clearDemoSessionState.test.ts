import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { clearDemoSessionState, isDemoUser } from "../clearDemoSessionState";

function installMemoryStorage() {
  const store = new Map<string, string>();
  const mock: Storage = {
    get length() {
      return store.size;
    },
    clear: () => store.clear(),
    getItem: (key) => store.get(key) ?? null,
    key: (index) => Array.from(store.keys())[index] ?? null,
    removeItem: (key) => void store.delete(key),
    setItem: (key, value) => void store.set(key, String(value)),
  };
  Object.defineProperty(window, "localStorage", { configurable: true, writable: true, value: mock });
}

describe("isDemoUser", () => {
  it("returns false when both demoMode and isTenant are false", () => {
    expect(isDemoUser(false, false)).toBe(false);
  });

  it("returns false when demoMode is true and isTenant is false", () => {
    expect(isDemoUser(true, false)).toBe(false);
  });

  it("returns false when demoMode is false and isTenant is true", () => {
    expect(isDemoUser(false, true)).toBe(false);
  });

  it("returns true only when both demoMode and isTenant are true", () => {
    expect(isDemoUser(true, true)).toBe(true);
  });
});

describe("clearDemoSessionState", () => {
  beforeEach(() => {
    installMemoryStorage();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it("removes all known persisted store keys", () => {
    const keys = ["arthur-user-settings", "arthur-theme", "arthur-task-list", "arthur-tour-panel"];
    for (const key of keys) {
      localStorage.setItem(key, "value");
    }

    clearDemoSessionState();

    for (const key of keys) {
      expect(localStorage.getItem(key)).toBeNull();
    }
  });

  it("removes standalone keys", () => {
    localStorage.setItem("arthur:task-tour:status", "completed");
    localStorage.setItem("task-tour:recipient-name", "Alex");

    clearDemoSessionState();

    expect(localStorage.getItem("arthur:task-tour:status")).toBeNull();
    expect(localStorage.getItem("task-tour:recipient-name")).toBeNull();
  });

  it("removes dynamic keys matching traces-welcome-* prefix", () => {
    localStorage.setItem("traces-welcome-abc123", "true");
    localStorage.setItem("traces-welcome-xyz", "true");

    clearDemoSessionState();

    expect(localStorage.getItem("traces-welcome-abc123")).toBeNull();
    expect(localStorage.getItem("traces-welcome-xyz")).toBeNull();
  });

  it("does not remove unrelated keys", () => {
    localStorage.setItem("arthur_auth_token", "token123");
    localStorage.setItem("arthur_auth_me", '{"name":"test"}');
    localStorage.setItem("some-other-key", "value");

    clearDemoSessionState();

    expect(localStorage.getItem("arthur_auth_token")).toBe("token123");
    expect(localStorage.getItem("arthur_auth_me")).toBe('{"name":"test"}');
    expect(localStorage.getItem("some-other-key")).toBe("value");
  });
});
