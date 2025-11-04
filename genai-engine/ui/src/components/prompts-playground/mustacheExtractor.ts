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

/**
 * Extracts keywords from mustache braces in a text string
 * @param text - The input text to search for mustache keywords
 * @returns An object containing:
 *   - hasKeywords: boolean indicating if any mustache keywords were found
 *   - keywords: array of unique keywords found
 *   - matches: array of all matches with their positions
 */
export function extractMustacheKeywords(text: string): {
  hasKeywords: boolean;
  keywords: string[];
  matches: Array<{ keyword: string; startIndex: number; endIndex: number }>;
} {
  const matches: Array<{
    keyword: string;
    startIndex: number;
    endIndex: number;
  }> = [];
  const keywordSet = new Set<string>();
  let match;

  // Find all matches
  while ((match = MUSTACHE_REGEX.exec(text)) !== null) {
    const keyword = match[1].trim(); // Remove any whitespace
    const startIndex = match.index;
    const endIndex = match.index + match[0].length;

    matches.push({ keyword, startIndex, endIndex });
    keywordSet.add(keyword);
  }

  return {
    hasKeywords: matches.length > 0,
    keywords: Array.from(keywordSet),
    matches,
  };
}

export default extractMustacheKeywords;
