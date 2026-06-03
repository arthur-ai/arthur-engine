import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { getStoredRecipientName, storeRecipientName } from "./recipientName";

// jsdom in this project ships a non-functional `localStorage` stub, so install
// a fresh in-memory implementation per test (mirrors how the tour-state-plugin
// tests inject their own storage).
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

describe("recipientName storage", () => {
  beforeEach(() => {
    installMemoryStorage();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it("returns null when nothing has been stored", () => {
    expect(getStoredRecipientName()).toBeNull();
  });

  it("round-trips a stored name", () => {
    storeRecipientName("Alex Rivera");
    expect(getStoredRecipientName()).toBe("Alex Rivera");
  });

  it("trims surrounding whitespace on write and read", () => {
    storeRecipientName("  Alex Rivera  ");
    expect(getStoredRecipientName()).toBe("Alex Rivera");
  });

  it("ignores empty or whitespace-only names without overwriting an existing value", () => {
    storeRecipientName("Alex Rivera");
    storeRecipientName("   ");
    expect(getStoredRecipientName()).toBe("Alex Rivera");
  });
});
