import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { waitForElement } from "./waitForElement";

describe("waitForElement", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("resolves immediately when the element already exists", async () => {
    const target = document.createElement("div");
    target.id = "tour-target";
    document.body.appendChild(target);

    const element = await waitForElement("#tour-target");
    expect(element).toBe(target);
  });

  it("rejects when the element is not found before timeout", async () => {
    vi.useFakeTimers();

    const promise = waitForElement("#missing-target", { timeoutMs: 50 });
    const assertion = expect(promise).rejects.toThrow("Tour target not found: #missing-target");

    await vi.runAllTimersAsync();
    await assertion;
  });
});
