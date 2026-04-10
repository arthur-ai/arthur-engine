import { createTool } from '@mastra/core/tools';
import { z } from 'zod';
import fs from 'node:fs';
import path from 'node:path';

const IGNORED_DIRS = new Set([
  'node_modules',
  '__pycache__',
  '.git',
  'dist',
  'build',
  '.venv',
  'venv',
  '.mypy_cache',
  '.ruff_cache',
  'coverage',
  '.next',
  '.turbo',
]);

function listFilesRecursive(dir: string, maxDepth = 4, depth = 0): string[] {
  if (depth >= maxDepth) return [];
  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return [];
  }
  const files: string[] = [];
  for (const entry of entries) {
    if (entry.name.startsWith('.') && entry.name !== '.env.example') continue;
    if (IGNORED_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...listFilesRecursive(full, maxDepth, depth + 1));
    } else {
      files.push(full);
    }
  }
  return files;
}

export const readFileTool = createTool({
  id: 'readFile',
  description: 'Read the contents of a file in the repository. Provide the path relative to repoPath.',
  inputSchema: z.object({
    repoPath: z.string().describe('Absolute path to the repository root'),
    filePath: z.string().describe('Path relative to the repository root'),
  }),
  execute: async (input) => {
    const { repoPath, filePath } = input as { repoPath: string; filePath: string };
    const full = path.join(repoPath, filePath);
    if (!fs.existsSync(full)) return { content: null, error: 'File not found' };
    try {
      const content = fs.readFileSync(full, 'utf-8');
      // Limit to 8000 chars to avoid huge files consuming context
      return { content: content.slice(0, 8000), error: null };
    } catch (e) {
      return { content: null, error: String(e) };
    }
  },
});

export const listDirectoryTool = createTool({
  id: 'listDirectory',
  description: 'List all files in the repository (up to 4 levels deep, skipping node_modules etc.)',
  inputSchema: z.object({
    repoPath: z.string().describe('Absolute path to the repository root'),
    subPath: z.string().describe('Subdirectory relative to repoPath, or "" for root').optional(),
  }),
  execute: async (input) => {
    const { repoPath, subPath } = input as { repoPath: string; subPath?: string };
    const base = subPath ? path.join(repoPath, subPath) : repoPath;
    const files = listFilesRecursive(base).map(f => path.relative(repoPath, f));
    return { files: files.slice(0, 300) };
  },
});

export const searchPatternTool = createTool({
  id: 'searchPattern',
  description: 'Search for a regex pattern across files in the repository. Returns file paths with matches.',
  inputSchema: z.object({
    repoPath: z.string().describe('Absolute path to the repository root'),
    pattern: z.string().describe('Regular expression pattern to search for'),
    fileExtensions: z
      .array(z.string())
      .describe('File extensions to search, e.g. [".py", ".ts"]. Empty = all files.')
      .optional(),
  }),
  execute: async (input) => {
    const { repoPath, pattern, fileExtensions } = input as {
      repoPath: string;
      pattern: string;
      fileExtensions?: string[];
    };
    const regex = new RegExp(pattern, 'i');
    const exts = fileExtensions ?? [];
    const allFiles = listFilesRecursive(repoPath);
    const filtered = exts.length > 0 ? allFiles.filter(f => exts.some(e => f.endsWith(e))) : allFiles;

    const matches: string[] = [];
    for (const file of filtered) {
      if (matches.length >= 20) break;
      try {
        const content = fs.readFileSync(file, 'utf-8');
        if (regex.test(content)) {
          matches.push(path.relative(repoPath, file));
        }
      } catch {
        // skip unreadable files
      }
    }
    return { matches, found: matches.length > 0 };
  },
});

export const checkDependenciesTool = createTool({
  id: 'checkDependencies',
  description: 'Read the project dependency manifest: package.json (Node) or requirements.txt / pyproject.toml (Python).',
  inputSchema: z.object({
    repoPath: z.string().describe('Absolute path to the repository root'),
  }),
  execute: async (input) => {
    const { repoPath } = input as { repoPath: string };
    const candidates = [
      'package.json',
      'requirements.txt',
      'pyproject.toml',
      'setup.py',
      'setup.cfg',
      'Pipfile',
    ];
    const found: Record<string, string> = {};
    for (const c of candidates) {
      const fp = path.join(repoPath, c);
      if (fs.existsSync(fp)) {
        try {
          found[c] = fs.readFileSync(fp, 'utf-8').slice(0, 4000);
        } catch {
          // skip
        }
      }
    }
    return { manifests: found };
  },
});
