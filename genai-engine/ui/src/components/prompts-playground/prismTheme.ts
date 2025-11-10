import vs from "react-syntax-highlighter/dist/esm/styles/prism/vs";

// Color values for consistent styling
export const vsThemeColors = {
  punctuation: "#0000ff", // Blue for braces and punctuation
  variable: "#A31515", // Red for variable names
  string: "#A31515", // Red for strings
  keyword: "#0000ff", // Blue for keywords
  property: "#ff0000", // Red for properties
  classname: "#2B91AF", // Blue-gray for class names
};

// Custom VS theme with blue braces and red variables
export const vsTheme = {
  ...vs,
  punctuation: {
    color: vsThemeColors.punctuation,
  },
  variable: {
    color: vsThemeColors.variable,
  },
};
