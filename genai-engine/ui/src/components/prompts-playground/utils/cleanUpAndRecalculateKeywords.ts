import { PromptType } from "../types";

/**
 * Helper function to clean up keywordTracker and recalculate keywords based on current prompts.
 * Removes stale entries for deleted messages and updates the keywords map.
 *
 * @param prompts - Current array of prompts
 * @param keywordTracker - Current keyword tracker map
 * @param keywords - Current keywords map
 * @param updateTracker - Optional function to update keywordTracker before cleanup (e.g., set variables for specific message IDs)
 * @returns Object with cleaned keywordTracker and keywords maps
 */
const cleanupAndRecalculateKeywords = (
  prompts: PromptType[],
  keywordTracker: Map<string, Array<string>>,
  keywords: Map<string, string>,
  updateTracker?: (tracker: Map<string, Array<string>>) => void
): {
  keywordTracker: Map<string, Array<string>>;
  keywords: Map<string, string>;
} => {
  // Create new keyword tracker without mutating state
  const newKeywordTracker = new Map<string, Array<string>>(keywordTracker);

  // Apply any custom updates to the tracker (e.g., set variables for specific message IDs)
  if (updateTracker) {
    updateTracker(newKeywordTracker);
  }

  // Get all message IDs from all prompts to identify which messages still exist
  const allCurrentMessageIds = new Set<string>();
  prompts.forEach((p) => {
    p.messages.forEach((msg) => allCurrentMessageIds.add(msg.id));
  });

  // Remove keywordTracker entries for message IDs that no longer exist in any prompt
  // This cleans up entries for deleted messages
  for (const [messageId] of newKeywordTracker.entries()) {
    if (!allCurrentMessageIds.has(messageId)) {
      newKeywordTracker.delete(messageId);
    }
  }

  // Collect all keywords that are currently in use across all messages
  const inUseKeywords = new Set<string>();
  newKeywordTracker.forEach((keywords) => {
    keywords.forEach((keyword) => inUseKeywords.add(keyword));
  });

  // Build new keywords map starting with existing keywords to preserve all values
  const newKeywords = new Map<string, string>(keywords);

  // Add any new keywords from messages that don't exist yet
  inUseKeywords.forEach((keyword) => {
    if (!newKeywords.has(keyword)) {
      newKeywords.set(keyword, "");
    }
  });

  // Remove keywords that are not in use in any message
  for (const keyword of newKeywords.keys()) {
    if (!inUseKeywords.has(keyword)) {
      newKeywords.delete(keyword);
    }
  }

  return {
    keywordTracker: newKeywordTracker,
    keywords: newKeywords,
  };
};

export default cleanupAndRecalculateKeywords;
