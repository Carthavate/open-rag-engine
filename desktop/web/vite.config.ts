import { defineConfig } from "vitest/config";
import type { Plugin } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

/** The built page may load only its own files and may not connect anywhere: it reaches the engine through WebView2
 * messages, so even a compromised dependency couldn't send documents off the computer. Build only, because the dev
 * server needs inline scripts and a websocket. */
const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'none'",
  "object-src 'none'",
  "base-uri 'none'",
  "form-action 'none'",
].join("; ");

const contentSecurityPolicy: Plugin = {
  name: "content-security-policy",
  apply: "build",
  transformIndexHtml: (html) =>
    html.replace("<head>", `<head>\n    <meta http-equiv="Content-Security-Policy" content="${CONTENT_SECURITY_POLICY}" />`),
};

// base "./" because the built files are served from the Open RAG app's folder, not a web server root.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss(), contentSecurityPolicy],
  server: { port: 5176, strictPort: true },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
