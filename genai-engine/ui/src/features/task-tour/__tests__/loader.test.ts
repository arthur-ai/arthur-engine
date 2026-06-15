import { describe, expect, it } from "vitest";

import { parseFrontmatter, TASK_TOUR_SECTIONS } from "../content/loader";

const TEST_FILE = "test.md";

function expectParseError(raw: string, messageSubstring: string): void {
  expect(() => parseFrontmatter(TEST_FILE, raw)).toThrow(expect.objectContaining({ message: expect.stringContaining(messageSubstring) }));
}

describe("parseFrontmatter", () => {
  it("parses a valid minimal mapping and body", () => {
    const raw = "---\nid: x\n---\n## intro\nHello\n";
    expect(parseFrontmatter(TEST_FILE, raw)).toEqual({
      data: { id: "x" },
      content: "## intro\nHello\n",
    });
  });

  it("parses CRLF delimiters", () => {
    const raw = "---\r\nid: x\r\n---\r\n## intro\r\nHello\r\n";
    expect(parseFrontmatter(TEST_FILE, raw)).toEqual({
      data: { id: "x" },
      content: "## intro\nHello\n",
    });
  });

  it("parses UTF-8 BOM-prefixed frontmatter", () => {
    const raw = `\uFEFF---\nid: x\n---\n## intro\nHello\n`;
    expect(parseFrontmatter(TEST_FILE, raw)).toEqual({
      data: { id: "x" },
      content: "## intro\nHello\n",
    });
  });

  it("returns empty data when no frontmatter delimiters are present", () => {
    const raw = "## intro\nHello\n";
    expect(parseFrontmatter(TEST_FILE, raw)).toEqual({
      data: {},
      content: raw,
    });
  });

  it("returns empty data for an empty frontmatter block", () => {
    const raw = "---\n---\n## intro\nHello\n";
    expect(parseFrontmatter(TEST_FILE, raw)).toEqual({
      data: {},
      content: "## intro\nHello\n",
    });
  });

  it("throws when the closing --- delimiter is missing", () => {
    expectParseError("---\nid: x\n## intro\n", "missing a closing --- delimiter");
  });

  it("throws on malformed YAML", () => {
    expectParseError('---\nid: "unclosed\n---\n', "failed to parse frontmatter");
  });

  it("throws when frontmatter root is a scalar", () => {
    expectParseError("---\nhello\n---\n", "must be a YAML mapping");
  });

  it("throws when frontmatter root is a list", () => {
    expectParseError("---\n- a\n---\n", "must be a YAML mapping");
  });

  it("throws on YAML alias nodes", () => {
    const raw = "---\ndefault: &a\n  id: x\nref: *a\n---\n";
    expectParseError(raw, "failed to parse frontmatter");
  });

  it("throws on YAML merge keys", () => {
    const raw = "---\nbase: &base\n  id: x\nchild:\n  <<: *base\n---\n";
    expectParseError(raw, "failed to parse frontmatter");
  });
});

describe("task tour content loader", () => {
  it("loads all real section markdown files", () => {
    expect(TASK_TOUR_SECTIONS.length).toBeGreaterThan(0);
    expect(TASK_TOUR_SECTIONS.every((section) => section.id.length > 0)).toBe(true);
  });
});
