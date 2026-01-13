import type { SavedRagConfigOutput, UnsavedRagConfigResponse, RagEvalResultSummaries } from "@/lib/api-client/api-client";

/**
 * Union type for RAG configurations (saved or unsaved)
 */
export type RagConfig = ({ type: "saved" } & SavedRagConfigOutput) | ({ type: "unsaved" } & UnsavedRagConfigResponse);

/**
 * Formats a RAG config for display in chips and lists.
 * For saved configs: shows truncated ID with version.
 * For unsaved configs: shows truncated ID or fallback.
 */
export function formatRagConfigName(config: RagConfig): string {
  if (config.type === "saved") {
    return `Config ${config.setting_configuration_id.slice(0, 8)} (v${config.version})`;
  } else {
    return config.unsaved_id ? `Unsaved ${config.unsaved_id.slice(0, 8)}` : "Unsaved Config";
  }
}

/**
 * Gets the display name for a RAG config from evaluation summary data.
 * Attempts to find the matching config from the configs array for full details.
 */
export function getRagConfigDisplayName(summary: RagEvalResultSummaries, configs: RagConfig[]): string {
  if (summary.rag_config_type === "saved" && summary.setting_configuration_id) {
    const matchingConfig = configs.find(
      (c) =>
        c.type === "saved" &&
        (c as SavedRagConfigOutput).setting_configuration_id === summary.setting_configuration_id &&
        (c as SavedRagConfigOutput).version === summary.setting_configuration_version
    );
    if (matchingConfig) {
      return formatRagConfigName(matchingConfig);
    }
    return `Config v${summary.setting_configuration_version}`;
  }
  return "Unsaved Config";
}
