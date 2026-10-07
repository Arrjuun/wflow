import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev:   `npm run dev` (port 5173) proxies /api to FastAPI on :8000.
// Build: output goes into the backend, which serves it at /static and renders index.html as a template.
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === "build" ? "/static/" : "/",
  build: { outDir: "../backend/app/static", emptyOutDir: true, manifest: true },
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
}));
