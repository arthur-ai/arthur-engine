import { NuqsAdapter } from "nuqs/adapters/react";
import { StrictMode } from "react";
import "./index.css";
import { createRoot } from "react-dom/client";

import App from "./App.tsx";
import { initAmplitude } from "./services/amplitude";

// Initialize Amplitude before rendering the app
initAmplitude();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <NuqsAdapter>
      <App />
    </NuqsAdapter>
  </StrictMode>
);
