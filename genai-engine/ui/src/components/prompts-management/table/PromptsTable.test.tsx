import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import PromptsTable from "./PromptsTable";

import { TOUR_IDS } from "@/features/task-tour/selectors";
import type { LLMGetAllMetadataResponse } from "@/lib/api-client/api-client";

vi.mock("@arthur/shared-components", () => ({
  DATE_FORMAT_12H_TIMEZONE: "",
  DATE_FORMAT_24H_TIMEZONE: "",
  DATE_FORMAT_24H_UTC: "",
  capitalize: (value: string) => value,
  formatDate: (value: string) => value,
  formatDuration: (value: string) => value,
  formatTimestampDuration: (value: string) => value,
  formatUTCTimestamp: (value: string) => value,
  truncateText: (value: string) => value,
}));

vi.mock("@/contexts/DisplaySettingsContext", () => ({
  useDisplaySettings: () => ({
    timezone: "UTC",
    use24Hour: true,
  }),
}));

vi.mock("@/utils/formatters", () => ({
  formatDateInTimezone: (value: string) => value,
}));

function promptMetadata(name: string, latestVersionCreatedAt: string): LLMGetAllMetadataResponse {
  return {
    created_at: "2026-01-01T00:00:00.000Z",
    deleted_versions: [],
    latest_version_created_at: latestVersionCreatedAt,
    name,
    tags: [],
    versions: 1,
  };
}

describe("PromptsTable", () => {
  it("marks the demo_task_prompt row as the tour target instead of the first row", () => {
    render(
      <PromptsTable
        prompts={[promptMetadata("newer_prompt", "2026-01-03T00:00:00.000Z"), promptMetadata("demo_task_prompt", "2026-01-02T00:00:00.000Z")]}
        sortColumn="latest_version_created_at"
        sortDirection="desc"
        onSort={vi.fn()}
        onExpandToFullScreen={vi.fn()}
      />
    );

    const demoRow = screen.getByText("demo_task_prompt").closest("tr");
    const firstRow = screen.getByText("newer_prompt").closest("tr");

    expect(demoRow?.getAttribute("data-tour-id")).toBe(TOUR_IDS.promptsFirstRow);
    expect(firstRow?.getAttribute("data-tour-id")).toBeNull();
  });
});
