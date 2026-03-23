import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import { useTheme } from "@mui/material/styles";
import { Highlight as PrismHighlight, themes } from "prism-react-renderer";

export const Highlight = ({ code, language, unwrapped = false }: { code: string; language: string; unwrapped?: boolean }) => {
  const theme = useTheme();
  const prismTheme = theme.palette.mode === "dark" ? themes.vsDark : themes.github;

  return (
    <PrismHighlight theme={prismTheme} code={code} language={language}>
      {({ tokens, getLineProps, getTokenProps }) => {
        const content = tokens.map((line, i) => (
          <Box key={i} {...getLineProps({ line, key: i })}>
            {line.map((token, key) => (
              <span key={key} {...getTokenProps({ token, key })} />
            ))}
          </Box>
        ));

        if (unwrapped) {
          return (
            <Box component="pre" sx={{ fontSize: "12px", textWrap: "wrap", m: 0 }}>
              {content}
            </Box>
          );
        }

        return (
          <Paper component="pre" variant="outlined" sx={{ fontSize: "12px", textWrap: "wrap", p: 2, overflow: "auto" }}>
            {content}
          </Paper>
        );
      }}
    </PrismHighlight>
  );
};
