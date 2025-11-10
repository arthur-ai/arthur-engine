import { v4 as uuidv4 } from "uuid";

import convertToolChoiceForBackend from "./convertToolChoiceForBackend";
import extractContext from "./extractContext";
import extractStatusCode from "./extractStatusCode";
import filterNullParams from "./filterNullParams";
import getToolChoiceDisplayValue from "./getToolChoiceDisplayValue";
import { extractMustacheKeywords, replaceKeywords } from "./mustacheExtractor";
import toBackendPrompt from "./toBackendPrompt";
import toCompletionRequest from "./toCompletionRequest";
import toFrontendPrompt from "./toFrontendPrompt";

const generateId = (type: "msg" | "tool") => {
  return type + "-" + uuidv4();
};

const arrayUtils = {
  moveItem: <T>(array: T[], fromIndex: number, toIndex: number): T[] => {
    const newArray = [...array];
    const [item] = newArray.splice(fromIndex, 1);
    newArray.splice(toIndex, 0, item);
    return newArray;
  },

  duplicateAfter: <T>(array: T[], originalIndex: number, duplicate: T): T[] => [
    ...array.slice(0, originalIndex + 1),
    duplicate,
    ...array.slice(originalIndex + 1),
  ],
};

export {
  extractMustacheKeywords,
  replaceKeywords,
  extractStatusCode,
  extractContext,
  getToolChoiceDisplayValue,
  toBackendPrompt,
  toCompletionRequest,
  toFrontendPrompt,
  generateId,
  arrayUtils,
  convertToolChoiceForBackend,
  filterNullParams,
};
