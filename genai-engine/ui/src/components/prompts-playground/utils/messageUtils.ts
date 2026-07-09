import { MessageType } from "../types";

import { OpenAIMessageInput, OpenAIMessageItem } from "@/lib/api-client/api-client";

/**
 * Converts MessageType[] to OpenAIMessageInput[] by stripping frontend-specific fields
 * (id and disabled) that are not needed for API calls.
 *
 * @param messages - Array of MessageType messages from the frontend
 * @returns Array of OpenAIMessageInput messages ready for API calls
 */
export const convertMessagesToApiFormat = (messages: MessageType[]): OpenAIMessageInput[] => {
  return messages.map((msg) => {
    // Strip id and disabled fields, keep all other OpenAIMessageInput fields
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { id, disabled, ...apiMessage } = msg;
    return apiMessage;
  });
};

/**
 * Regex patterns to detect template variables
 * - Mustache/Jinja2 variables: {{ variable }}
 * - Jinja2 statements: {% statement %}
 */
const MUSTACHE_VARIABLE_PATTERN = /\{\{[^}]+\}\}/;
const JINJA_STATEMENT_PATTERN = /\{%[^%]+%\}/;

/**
 * Checks if a text string contains any template patterns (mustache or jinja).
 *
 * @param text - The text to check
 * @returns true if the text contains template patterns, false otherwise
 */
const hasTemplatePatterns = (text: string): boolean => {
  return MUSTACHE_VARIABLE_PATTERN.test(text) || JINJA_STATEMENT_PATTERN.test(text);
};

/**
 * Checks if messages contain any template patterns (mustache or jinja).
 * This is used to optimize API calls by skipping variable extraction when no templates are present.
 *
 * @param messages - Array of MessageType messages to check
 * @returns true if any message contains template patterns, false otherwise
 */
export const hasTemplateVariables = (messages: MessageType[]): boolean => {
  if (messages.length === 0) {
    return false;
  }

  for (const message of messages) {
    if (!message.content) {
      continue;
    }

    if (typeof message.content === "string") {
      if (hasTemplatePatterns(message.content)) {
        return true;
      }
    } else if (Array.isArray(message.content)) {
      // Check OpenAIMessageItem[] content
      for (const item of message.content) {
        if (item.text && typeof item.text === "string" && hasTemplatePatterns(item.text)) {
          return true;
        }
      }
    }
  }

  // Also check tool_calls — templates can live in a tool call's arguments.
  for (const message of messages) {
    for (const toolCall of message.tool_calls ?? []) {
      if (hasTemplatePatterns(toolCall.function.arguments)) {
        return true;
      }
    }
  }

  return false;
};

/**
 * Splits message content into an editable text string and the list of non-text
 * (image/audio) attachments. Multiple text parts of an array are intentionally
 * consolidated into a single editable string (a limitation of the single-textarea
 * editor, not a silent bug); attachments are returned untouched.
 *
 * @param content - The message content (plain string or multimodal item array)
 * @returns The extracted text and the list of image/audio attachments
 */
export const splitMessageContent = (content: string | OpenAIMessageItem[] | null | undefined): { text: string; attachments: OpenAIMessageItem[] } => {
  if (!content) {
    return { text: "", attachments: [] };
  }

  if (typeof content === "string") {
    return { text: content, attachments: [] };
  }

  const textParts: string[] = [];
  const attachments: OpenAIMessageItem[] = [];
  for (const item of content) {
    if (item.type === "text") {
      textParts.push(item.text || "");
    } else if (item.type === "image_url" || item.type === "input_audio") {
      attachments.push(item);
    }
  }

  return { text: textParts.join(" "), attachments };
};

/**
 * Builds message content from an editable text string and its attachments.
 * When there are no attachments it returns a plain string (preserving today's
 * behavior and keeping variable extraction/templating working); otherwise it
 * returns a multimodal item array. The text is included as the first part only
 * when it is non-empty, so we never emit an empty text item alongside media.
 *
 * @param text - The editable text portion of the message
 * @param attachments - The image/audio attachments to include
 * @returns A plain string or a multimodal OpenAIMessageItem[]
 */
export const buildMessageContent = (text: string, attachments: OpenAIMessageItem[]): string | OpenAIMessageItem[] => {
  if (attachments.length === 0) {
    return text;
  }

  return text.trim() === "" ? [...attachments] : [{ type: "text", text }, ...attachments];
};

/**
 * Compares two message content values (plain string or multimodal array) for
 * equality without stringifying potentially multi-MB base64 payloads on every
 * keystroke. Text items are compared by value; image/audio attachments are
 * compared by reference, which is safe because their object identity is
 * preserved from load through build.
 *
 * @param a - The freshly composed content
 * @param b - The previously committed content
 * @returns true if the two contents are equivalent
 */
export const contentEquals = (a: string | OpenAIMessageItem[], b: string | OpenAIMessageItem[] | null | undefined): boolean => {
  if (b == null) {
    return false;
  }
  if (typeof a === "string" || typeof b === "string") {
    return a === b;
  }
  if (a.length !== b.length) {
    return false;
  }
  return a.every((item, i) => {
    const other = b[i];
    if (item.type !== other.type) {
      return false;
    }
    if (item.type === "text") {
      return (item.text ?? "") === (other.text ?? "");
    }
    // Attachment objects are reference-stable from load/build.
    return item === other;
  });
};

/**
 * Reads a File as a data URL using FileReader.
 *
 * @param file - The file to read
 * @returns A promise resolving to the file's data URL
 */
const readFileAsDataUrl = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error ?? new Error("Failed to read file"));
    reader.readAsDataURL(file);
  });
};

/**
 * Converts an image File into an image_url OpenAIMessageItem. The image is
 * embedded as a data URL so it can be sent inline to vision-capable models.
 *
 * @param file - The image file to convert
 * @returns A promise resolving to an image_url message item
 */
export const fileToImageItem = async (file: File): Promise<OpenAIMessageItem> => {
  const dataUrl = await readFileAsDataUrl(file);
  return {
    type: "image_url",
    image_url: { url: dataUrl },
  };
};

// Maps common audio MIME types to the format string the backend expects.
const MIME_TO_AUDIO_FORMAT: Record<string, string> = {
  "audio/mpeg": "mp3",
  "audio/mp3": "mp3",
  "audio/wav": "wav",
  "audio/x-wav": "wav",
  "audio/wave": "wav",
  "audio/flac": "flac",
  "audio/x-flac": "flac",
  "audio/ogg": "ogg",
  "audio/webm": "webm",
  "audio/mp4": "mp4",
  "audio/aac": "aac",
};

/**
 * Resolves the backend audio format from a file, preferring the MIME type and
 * falling back to the file extension. Throws when neither yields a usable
 * format so the caller can surface an error instead of silently mislabeling.
 *
 * @param file - The audio file whose format should be resolved
 * @returns The resolved audio format string (e.g. 'mp3', 'wav')
 */
export const resolveAudioFormat = (file: File): string => {
  const byMime = MIME_TO_AUDIO_FORMAT[file.type.toLowerCase()];
  if (byMime) {
    return byMime;
  }
  const extension = file.name.includes(".") ? file.name.slice(file.name.lastIndexOf(".") + 1).toLowerCase() : "";
  if (extension) {
    return extension;
  }
  throw new Error(`Unable to determine audio format for "${file.name}"`);
};

/**
 * Converts an audio File into an input_audio OpenAIMessageItem. The audio is
 * stored as raw base64 (data URL prefix stripped) with the format derived from
 * the file's MIME type (falling back to its extension).
 *
 * @param file - The audio file to convert
 * @returns A promise resolving to an input_audio message item
 */
export const fileToAudioItem = async (file: File): Promise<OpenAIMessageItem> => {
  const format = resolveAudioFormat(file);
  const dataUrl = await readFileAsDataUrl(file);
  // Strip the "data:<mime>;base64," prefix; the backend expects raw base64.
  const base64 = dataUrl.includes(",") ? dataUrl.slice(dataUrl.indexOf(",") + 1) : dataUrl;
  return {
    type: "input_audio",
    input_audio: { data: base64, format },
  };
};
