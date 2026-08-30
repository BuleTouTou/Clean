import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import VueRouter from "unplugin-vue-router/vite";

export default defineConfig(({ command }) => ({
  plugins: [VueRouter({ routesFolder: "src/pages", watch: command === "serve" }), vue()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8765",
      "/download": "http://127.0.0.1:8765",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: "app.js",
        assetFileNames: "[name][extname]",
      },
    },
  },
}));
