import { StrictMode } from "react";
import "./index.css";
import { createRoot } from "react-dom/client";

import App from "./App.tsx";
import { initAnalytics } from "./services/analytics";

// Initialize analytics (Amplitude + session replay) before rendering the app
initAnalytics();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
