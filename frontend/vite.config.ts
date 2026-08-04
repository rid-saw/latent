import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

export default defineConfig({
  // GitHub Pages serves the demo from /<repo>/, not the domain root, so asset
  // URLs need that prefix. Set only by the deploy workflow — local dev and any
  // root-served build stay at "/".
  base: process.env.VITE_BASE || "/",
  // react-grid-layout's drag engine reads process.env at runtime; the browser
  // has no `process`, so every mousedown threw and dragging silently died.
  define: { "process.env": {} },
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: { port: 5173 },
});
