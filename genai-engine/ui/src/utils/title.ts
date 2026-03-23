import { DEFAULT_TITLE } from "@arthur/shared-components";

export function createTitle(title: string) {
  return title ? `${DEFAULT_TITLE} - ${title}` : DEFAULT_TITLE;
}
