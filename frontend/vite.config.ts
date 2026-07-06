import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

// In dev, proxy /api -> FastAPI control-plane (avoids CORS). Override the
// backend target with VITE_PROXY_TARGET. In production, set VITE_API_BASE_URL
// to the API origin (and enable CORS server-side) or serve behind one origin.
export default defineConfig(() => {
  const target = process.env.VITE_PROXY_TARGET || "http://localhost:8080";
  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
  };
});
