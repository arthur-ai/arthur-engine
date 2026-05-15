import { StrictMode } from "react";
import "./index.css";
import { createRoot } from "react-dom/client";

import App from "./App.tsx";
import { initAmplitude } from "./services/amplitude";

console.log("this is an Arthur Engine app");

// Initialize Amplitude before rendering the app
initAmplitude();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
