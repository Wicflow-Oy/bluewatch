import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The API runs on 8787 (uvicorn bluewatch.api.app:app). Keys never reach the browser.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8787" } },
});
