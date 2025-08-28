// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

export default defineConfig(({ mode }) => ({
  server: {
    host: "::",
    port: 8080,
    // Proxy DEV: tudo que começar com /api vai para o FastAPI em 8000.
    // Isso elimina CORS no dev e replica o cenário de produção.
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        // remove o /api antes de encaminhar (no backend não tem esse prefixo)
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
  plugins: [
    react(),
    mode === "development" && componentTagger(),
  ].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
}));
