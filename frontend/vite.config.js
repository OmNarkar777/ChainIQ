import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  build: {
    rollupOptions: {
      output: {
        // Split heavy vendor libraries into separate chunks so the browser
        // can cache them independently of app code changes.
        manualChunks: {
          "vendor-react":    ["react", "react-dom", "react-router-dom"],
          "vendor-recharts": ["recharts"],
          "vendor-markdown": ["react-markdown", "remark-gfm"],
          "vendor-icons":    ["lucide-react"],
        },
      },
    },
  },

  server: {
    host: true,
    proxy: {
      // Dev only: proxy /api/* → backend at localhost:8000
      "/api": {
        target:       "http://localhost:8000",
        changeOrigin: true,
        rewrite:      (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
