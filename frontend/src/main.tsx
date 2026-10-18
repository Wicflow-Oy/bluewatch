import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
// Fonts are served from this origin (the CSP allows no other), so first paint never waits on a third-party host.
import "./styles/fonts.css";
import "./styles/tokens.css";
import "./styles/base.css";

// A tab opened before a redeploy asks for chunks the new build no longer has. Reload once to pick up
// the new build; the time guard stops a loop when the chunk is missing for another reason.
const RELOADED_AT = "bluewatch.reloadedAt";
window.addEventListener("vite:preloadError", () => {
  try {
    const last = Number(window.sessionStorage.getItem(RELOADED_AT) ?? 0);
    if (Date.now() - last < 10_000) return;
    window.sessionStorage.setItem(RELOADED_AT, String(Date.now()));
  } catch {
    return; // without storage there is no loop guard, so the page's own error state stays
  }
  window.location.reload();
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
