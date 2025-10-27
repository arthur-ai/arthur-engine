import { Highlight } from "../Highlight";

import { TextMessageRenderer } from "./TextMessageRenderer";

import { Tabs } from "@/components/ui/Tabs";
import { type LLMOutputMessage } from "@/schemas/llm";
import { tryFormatJson } from "@/utils/llm";

const TAB_LABELS = {
  files: "Files",
  text: "Text",
  sources: "Sources",
  reasoning: "Reasoning",
  object: "Object",
} as const;

const PANEL_RENDERERS = {
  files: (content: LLMOutputMessage["files"]) => {
    return <Highlight code={tryFormatJson(content)} language="json" />;
  },
  text: (content: LLMOutputMessage["text"]) => (
    <TextMessageRenderer text={content} />
  ),
  sources: (content: LLMOutputMessage["sources"]) => (
    <Highlight code={tryFormatJson(content)} language="json" />
  ),
  reasoning: (content: LLMOutputMessage["reasoning"]) => (
    <Highlight code={tryFormatJson(content)} language="json" />
  ),
  object: (content: LLMOutputMessage["object"]) => (
    <Highlight code={tryFormatJson(content)} language="json" />
  ),
} satisfies Record<
  keyof LLMOutputMessage,
  (content: LLMOutputMessage[keyof LLMOutputMessage]) => React.ReactNode
>;

export const OutputMessageRenderer = ({
  message,
}: {
  message: LLMOutputMessage;
}) => {
  const entries = Object.entries(message)
    .filter(([, value]) => (Array.isArray(value) ? value.length > 0 : !!value))
    .map(([key, content]) => ({
      type: key as keyof LLMOutputMessage,
      content,
    }));

  return (
    <Tabs.Root defaultValue={entries[0].type}>
      <Tabs.List>
        {entries.map((entry) => (
          <Tabs.Tab key={entry.type} value={entry.type}>
            {TAB_LABELS[entry.type as keyof typeof TAB_LABELS]}
          </Tabs.Tab>
        ))}
        <Tabs.Tab value="raw">Raw</Tabs.Tab>
        <Tabs.Indicator />
      </Tabs.List>
      {entries.map((entry) => (
        <Tabs.Panel key={entry.type} value={entry.type}>
          {PANEL_RENDERERS[entry.type as keyof typeof PANEL_RENDERERS](
            entry.content
          )}
        </Tabs.Panel>
      ))}
      <Tabs.Panel value="raw">
        <Highlight code={tryFormatJson(message)} language="json" />
      </Tabs.Panel>
    </Tabs.Root>
  );
};
