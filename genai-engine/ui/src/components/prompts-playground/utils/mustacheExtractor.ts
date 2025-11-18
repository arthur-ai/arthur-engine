// Regex pattern to match {{keyword}} format
// \{\{ - matches literal {{
// ([^}]+) - captures one or more characters that are not }
// \}\} - matches literal }}
const MUSTACHE_REGEX = /\{\{([^}]+)\}\}/g;

// Regex pattern to match Jinja2/Nunjucks statements {% ... %}
const JINJA2_STATEMENT_REGEX = /\{%([^%]+)%\}/g;

// Jinja2/Nunjucks keywords that should NOT be treated as variables
const JINJA2_KEYWORDS = new Set([
  "if",
  "elif",
  "else",
  "endif",
  "for",
  "endfor",
  "in",
  "block",
  "endblock",
  "extends",
  "include",
  "import",
  "from",
  "macro",
  "endmacro",
  "call",
  "endcall",
  "filter",
  "endfilter",
  "set",
  "endset",
  "raw",
  "endraw",
  "with",
  "endwith",
  "autoescape",
  "endautoescape",
  "trans",
  "endtrans",
  "pluralize",
  "do",
  "break",
  "continue",
  "scoped",
  "ignore",
  "missing",
  "and",
  "or",
  "not",
  "is",
  "true",
  "false",
  "none",
  "True",
  "False",
  "None",
]);

/**
 * Extracts variable names from Jinja2/Nunjucks statement content
 * @param content - The content inside {% ... %}
 * @returns Array of variable names found
 */
function extractVariablesFromJinja2Statement(content: string): string[] {
  const variables: string[] = [];
  const trimmed = content.trim();

  // Skip if empty or just keywords
  if (!trimmed) return variables;

  // Split by operators and whitespace to get tokens
  // This regex splits on operators, parentheses, brackets, commas, etc.
  const tokens = trimmed.split(/[\s.|\-()[\]+,*/%=!<>&|]+/).filter((t) => t.length > 0);

  for (const token of tokens) {
    // Skip keywords
    if (JINJA2_KEYWORDS.has(token)) {
      continue;
    }

    // Skip string literals (quoted strings)
    if ((token.startsWith('"') && token.endsWith('"')) || (token.startsWith("'") && token.endsWith("'"))) {
      continue;
    }

    // Skip numeric literals
    if (/^-?\d+(\.\d+)?$/.test(token)) {
      continue;
    }

    // This looks like a variable name
    // Valid variable names: start with letter or underscore, followed by letters, digits, underscores
    if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(token)) {
      variables.push(token);
    }
  }

  return variables;
}

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
 * Extracts keywords from mustache braces and Jinja2 statements in a text string
 * @param text - The input text to search for mustache keywords and Jinja2 variables
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

  // Extract from Mustache variables {{ variable }}
  let match;
  while ((match = MUSTACHE_REGEX.exec(text)) !== null) {
    const keyword = match[1].trim(); // Remove any whitespace
    const startIndex = match.index;
    const endIndex = match.index + match[0].length;

    matches.push({ keyword, startIndex, endIndex });
    keywordSet.add(keyword);
  }

  // Extract from Jinja2 statements {% if variable %}, {% for item in items %}, etc.
  const jinja2Regex = new RegExp(JINJA2_STATEMENT_REGEX);
  while ((match = jinja2Regex.exec(text)) !== null) {
    const statementContent = match[1];
    const variables = extractVariablesFromJinja2Statement(statementContent);
    const startIndex = match.index;

    for (const variable of variables) {
      // Find the position of this variable within the statement
      const variableIndex = statementContent.indexOf(variable);
      if (variableIndex !== -1) {
        // Calculate the actual position in the text
        // {% is 2 chars, then variableIndex, then the variable length
        const actualStartIndex = startIndex + 2 + variableIndex;
        const actualEndIndex = actualStartIndex + variable.length;

        matches.push({
          keyword: variable,
          startIndex: actualStartIndex,
          endIndex: actualEndIndex,
        });
        keywordSet.add(variable);
      }
    }
  }

  return {
    hasKeywords: matches.length > 0,
    keywords: Array.from(keywordSet),
    matches,
  };
}

export default extractMustacheKeywords;
