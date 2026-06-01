import { beforeEach, describe, expect, it } from "vitest";

import { findElementByExactText, resolveTargetAsync, resolveTargetSync } from "../targets";

describe("tour target resolution", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("resolves selector, element, ref, and query hook targets synchronously", () => {
    const element = document.createElement("button");
    element.dataset.tourId = "target";
    document.body.appendChild(element);

    expect(resolveTargetSync({ kind: "selector", selector: "[data-tour-id='target']" })).toBe(element);
    expect(resolveTargetSync({ kind: "element", resolve: () => element })).toBe(element);
    expect(resolveTargetSync({ kind: "ref", ref: { current: element } })).toBe(element);
    expect(
      resolveTargetSync(
        { kind: "queryHook", hookId: "live-row" },
        {
          resolveQueryHook: (hookId) => (hookId === "live-row" ? () => element : undefined),
        }
      )
    ).toBe(element);
  });

  it("waits for selector targets to appear before timing out", async () => {
    const promise = resolveTargetAsync({ kind: "selector", selector: "[data-tour-id='late']" }, { timeoutMs: 100 });

    const element = document.createElement("button");
    element.dataset.tourId = "late";
    document.body.appendChild(element);

    await expect(promise).resolves.toBe(element);
  });

  it("polls query hook targets until a resolver returns an element", async () => {
    let element: Element | null = null;
    const promise = resolveTargetAsync(
      { kind: "queryHook", hookId: "virtual-row" },
      {
        timeoutMs: 100,
        resolveQueryHook: () => () => element,
      }
    );

    await new Promise<void>((resolve) => {
      window.requestAnimationFrame(() => {
        element = document.createElement("div");
        resolve();
      });
    });

    await expect(promise).resolves.toBe(element);
  });

  it("returns null on timeout or abort", async () => {
    await expect(resolveTargetAsync({ kind: "selector", selector: "[data-missing]" }, { timeoutMs: 1 })).resolves.toBeNull();

    const controller = new AbortController();
    const promise = resolveTargetAsync(
      { kind: "selector", selector: "[data-aborted]" },
      {
        timeoutMs: 100,
        signal: controller.signal,
      }
    );
    controller.abort();

    await expect(promise).resolves.toBeNull();
  });

  it("finds an element by exact normalized text and can return its closest ancestor", () => {
    document.body.innerHTML = `
      <table>
        <tbody>
          <tr data-row="other">
            <td>demo_task_prompt_v2</td>
          </tr>
          <tr data-row="target">
            <td>
              <span> demo_task_prompt </span>
            </td>
          </tr>
        </tbody>
      </table>
    `;

    expect(findElementByExactText("demo_task_prompt", { selector: "td", closestSelector: "tr" })).toBe(document.querySelector('[data-row="target"]'));
  });
});
