// Regex pattern to match {{keyword}} format
// \{\{ - matches literal {{
// ([^}]+) - captures one or more characters that are not }
// \}\} - matches literal }}
const MUSTACHE_REGEX = /\{\{([^}]+)\}\}/g;

/**
 * Replaces keywords in a text string with their corresponding values
 * @param text
 * @param keywords
 * @returns
 */
export const replaceKeywords = (text: string, keywords: Map<string, string>): string => {
  return text.replace(MUSTACHE_REGEX, (match, keyword) => {
    const value = keywords.get(keyword.trim());
    return value !== undefined ? value : match;
  });
};
