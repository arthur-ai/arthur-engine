import { DEFAULT_TITLE } from "@/components/traces/constants";

export function createTitle(title: string) {
  return title ? `${DEFAULT_TITLE} - ${title}` : DEFAULT_TITLE;
}
