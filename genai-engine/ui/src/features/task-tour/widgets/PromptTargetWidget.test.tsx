import { beforeEach, describe, expect, it } from "vitest";

import { TOUR_IDS } from "../selectors";

import {
  resolveCreateExperimentEntryTarget,
  resolveCreateExperimentFinalTarget,
  resolveCreateExperimentInfoTarget,
  resolveCreateExperimentPromptMappingsTarget,
  resolveDemoTaskPromptRowTarget,
  resolvePlaygroundPromptCardTarget,
  resolvePromptOpenInPlaygroundTarget,
  resolvePromptTagsTarget,
} from "./PromptTargetWidget";

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

  it("targets the prompt row whose name exactly matches demo_task_prompt", () => {
    document.body.innerHTML = `
      <table>
        <tbody>
          <tr data-row="first" data-tour-id="${TOUR_IDS.promptsFirstRow}">
            <td>other_prompt</td>
          </tr>
          <tr data-row="target">
            <th scope="row"><span>demo_task_prompt</span></th>
          </tr>
          <tr data-row="partial">
            <th scope="row"><span>demo_task_prompt_v2</span></th>
          </tr>
        </tbody>
      </table>
    `;

    expect(resolveDemoTaskPromptRowTarget()).toBe(document.querySelector('[data-row="target"]'));
  });

  it("targets demo_task_prompt when the name cell also renders a version chip", () => {
    document.body.innerHTML = `
      <table>
        <tbody>
          <tr data-row="first" data-tour-id="${TOUR_IDS.promptsFirstRow}">
            <th scope="row">
              <div>
                <div>other_prompt</div>
                <span>v4</span>
              </div>
            </th>
          </tr>
          <tr data-row="target">
            <th scope="row">
              <div>
                <div>demo_task_prompt</div>
                <span>v3</span>
              </div>
            </th>
          </tr>
        </tbody>
      </table>
    `;

    expect(resolveDemoTaskPromptRowTarget()).toBe(document.querySelector('[data-row="target"]'));
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

  it("targets Create New after the Experiment menu opens", () => {
    document.body.innerHTML = `<button data-tour-id="${TOUR_IDS.promptsExperimentButton}">Experiment</button>`;
    const trigger = document.querySelector("button");

    expect(resolveCreateExperimentEntryTarget()).toBe(trigger);

    document.body.innerHTML += `<button data-tour-id="${TOUR_IDS.promptsExperimentCreateNew}">Create New</button>`;
    expect(resolveCreateExperimentEntryTarget()).toBe(document.querySelector(`[data-tour-id="${TOUR_IDS.promptsExperimentCreateNew}"]`));
  });

  it("targets Create Experiment info step after the modal opens", () => {
    document.body.innerHTML = `<button data-tour-id="${TOUR_IDS.promptsExperimentButton}">Experiment</button>`;
    const trigger = document.querySelector("button");

    expect(resolveCreateExperimentInfoTarget()).toBe(trigger);

    document.body.innerHTML += `<section data-tour-id="${TOUR_IDS.createExperimentInfoStep}">Experiment Info</section>`;
    expect(resolveCreateExperimentInfoTarget()).toBe(document.querySelector(`[data-tour-id="${TOUR_IDS.createExperimentInfoStep}"]`));
  });

  it("targets Create Experiment prompt mappings after that modal section is visible", () => {
    document.body.innerHTML = `
      <section data-tour-id="${TOUR_IDS.createExperimentModal}">Create Experiment</section>
      <section data-tour-id="${TOUR_IDS.createExperimentPromptMappingsStep}">Prompt mappings</section>
    `;

    expect(resolveCreateExperimentPromptMappingsTarget()).toBe(
      document.querySelector(`[data-tour-id="${TOUR_IDS.createExperimentPromptMappingsStep}"]`)
    );
  });

  it("targets eval mappings for final create when present, otherwise the create button", () => {
    document.body.innerHTML = `
      <button data-tour-id="${TOUR_IDS.createExperimentSubmit}">Create Experiment</button>
    `;
    const createButton = document.querySelector("button");

    expect(resolveCreateExperimentFinalTarget()).toBe(createButton);

    document.body.innerHTML += `<section data-tour-id="${TOUR_IDS.createExperimentEvalMappingsStep}">Eval mappings</section>`;
    expect(resolveCreateExperimentFinalTarget()).toBe(document.querySelector(`[data-tour-id="${TOUR_IDS.createExperimentEvalMappingsStep}"]`));
  });
});
