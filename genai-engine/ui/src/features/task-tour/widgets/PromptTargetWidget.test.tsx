import { beforeEach, describe, expect, it } from "vitest";

import { TOUR_IDS } from "../selectors";

import { resolvePlaygroundPromptCardTarget, resolvePromptOpenInPlaygroundTarget, resolvePromptTagsTarget } from "./PromptTargetWidget";

describe("PromptTargetWidget resolvers", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("prefers Open in Playground but falls back while the prompt detail is still loading", () => {
    document.body.innerHTML = `<button data-tour-id="${TOUR_IDS.promptsFirstRow}">Prompt row</button>`;
    const row = document.querySelector("button");

    expect(resolvePromptOpenInPlaygroundTarget()).toBe(row);

    document.body.innerHTML += `<button data-tour-id="${TOUR_IDS.promptOpenInPlayground}">Open in Playground</button>`;
    expect(resolvePromptOpenInPlaygroundTarget()).toBe(document.querySelector(`[data-tour-id="${TOUR_IDS.promptOpenInPlayground}"]`));
  });

  it("targets the newest playground prompt card after Add Prompt creates one", () => {
    document.body.innerHTML = `
      <section data-tour-id="${TOUR_IDS.playgroundPromptCard}" data-prompt="original">Original</section>
      <section data-tour-id="${TOUR_IDS.playgroundPromptCard}" data-prompt="new">New</section>
    `;

    expect(resolvePlaygroundPromptCardTarget()).toBe(document.querySelector('[data-prompt="new"]'));
  });

  it("prefers the Prompt Tags popover after the tag trigger opens it", () => {
    document.body.innerHTML = `<button data-tour-id="${TOUR_IDS.promptAddTag}">Add tag</button>`;
    const trigger = document.querySelector("button");

    expect(resolvePromptTagsTarget()).toBe(trigger);

    document.body.innerHTML += `<section data-tour-id="${TOUR_IDS.promptTagsPopover}">Prompt Tags</section>`;
    expect(resolvePromptTagsTarget()).toBe(document.querySelector(`[data-tour-id="${TOUR_IDS.promptTagsPopover}"]`));
  });
});
