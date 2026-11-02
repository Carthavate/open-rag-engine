import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// base "./" because the built files are served from the Open RAG app's folder, not a web server root.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  server: { port: 5176, strictPort: true },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
