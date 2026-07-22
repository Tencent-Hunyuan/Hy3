import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";


const root = document.getElementById("root");
if (root === null) {
  throw new Error("ReplayLab root element was not found");
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
