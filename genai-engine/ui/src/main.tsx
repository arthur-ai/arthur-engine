import { StrictMode } from "react";
import "./index.css";
import { createRoot } from "react-dom/client";
import { Toaster } from "sonner";

import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
    <Toaster position="bottom-center" richColors />
  </StrictMode>
);
