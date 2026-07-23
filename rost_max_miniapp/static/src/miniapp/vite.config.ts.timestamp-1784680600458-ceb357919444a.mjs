// vite.config.ts
import { defineConfig } from "file:///home/nnm/odoo-dev/addons/rost_max_miniapp/static/src/miniapp/node_modules/vite/dist/node/index.js";
import react from "file:///home/nnm/odoo-dev/addons/rost_max_miniapp/static/src/miniapp/node_modules/@vitejs/plugin-react/dist/index.js";
import path from "path";
var __vite_injected_original_dirname = "/home/nnm/odoo-dev/addons/rost_max_miniapp/static/src/miniapp";
var vite_config_default = defineConfig({
  plugins: [react()],
  resolve: {
    extensions: [".tsx", ".ts", ".jsx", ".js", ".json"],
    alias: {
      "@": path.resolve(__vite_injected_original_dirname, "."),
      "@/components": path.resolve(__vite_injected_original_dirname, "./components"),
      "@/lib": path.resolve(__vite_injected_original_dirname, "./lib"),
      "@/pages": path.resolve(__vite_injected_original_dirname, "./pages")
    }
  },
  base: "/rost_max_miniapp/static/src/bundle/",
  build: {
    outDir: "../bundle",
    emptyOutDir: true,
    rollupOptions: {
      input: "./main.tsx",
      output: {
        format: "umd",
        entryFileNames: "index.js",
        assetFileNames: "styles.css"
      }
    }
  },
  server: {
    port: 5173,
    hmr: false
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCIvaG9tZS9ubm0vb2Rvby1kZXYvYWRkb25zL3Jvc3RfbWF4X21pbmlhcHAvc3RhdGljL3NyYy9taW5pYXBwXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCIvaG9tZS9ubm0vb2Rvby1kZXYvYWRkb25zL3Jvc3RfbWF4X21pbmlhcHAvc3RhdGljL3NyYy9taW5pYXBwL3ZpdGUuY29uZmlnLnRzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy9ob21lL25ubS9vZG9vLWRldi9hZGRvbnMvcm9zdF9tYXhfbWluaWFwcC9zdGF0aWMvc3JjL21pbmlhcHAvdml0ZS5jb25maWcudHNcIjtpbXBvcnQgeyBkZWZpbmVDb25maWcgfSBmcm9tICd2aXRlJ1xuaW1wb3J0IHJlYWN0IGZyb20gJ0B2aXRlanMvcGx1Z2luLXJlYWN0J1xuaW1wb3J0IHBhdGggZnJvbSAncGF0aCdcblxuZXhwb3J0IGRlZmF1bHQgZGVmaW5lQ29uZmlnKHtcbiAgcGx1Z2luczogW3JlYWN0KCldLFxuICByZXNvbHZlOiB7XG4gICAgZXh0ZW5zaW9uczogWycudHN4JywgJy50cycsICcuanN4JywgJy5qcycsICcuanNvbiddLFxuICAgIGFsaWFzOiB7XG4gICAgICAnQCc6IHBhdGgucmVzb2x2ZShfX2Rpcm5hbWUsICcuJyksXG4gICAgICAnQC9jb21wb25lbnRzJzogcGF0aC5yZXNvbHZlKF9fZGlybmFtZSwgJy4vY29tcG9uZW50cycpLFxuICAgICAgJ0AvbGliJzogcGF0aC5yZXNvbHZlKF9fZGlybmFtZSwgJy4vbGliJyksXG4gICAgICAnQC9wYWdlcyc6IHBhdGgucmVzb2x2ZShfX2Rpcm5hbWUsICcuL3BhZ2VzJyksXG4gICAgfSxcbiAgfSxcbiAgYmFzZTogJy9yb3N0X21heF9taW5pYXBwL3N0YXRpYy9zcmMvYnVuZGxlLycsXG4gIGJ1aWxkOiB7XG4gICAgb3V0RGlyOiAnLi4vYnVuZGxlJyxcbiAgICBlbXB0eU91dERpcjogdHJ1ZSxcbiAgICByb2xsdXBPcHRpb25zOiB7XG4gICAgICBpbnB1dDogJy4vbWFpbi50c3gnLFxuICAgICAgb3V0cHV0OiB7XG4gICAgICAgIGZvcm1hdDogJ3VtZCcsXG4gICAgICAgIGVudHJ5RmlsZU5hbWVzOiAnaW5kZXguanMnLFxuICAgICAgICBhc3NldEZpbGVOYW1lczogJ3N0eWxlcy5jc3MnLFxuICAgICAgfSxcbiAgICB9LFxuICB9LFxuICBzZXJ2ZXI6IHtcbiAgICBwb3J0OiA1MTczLFxuICAgIGhtcjogZmFsc2UsXG4gIH0sXG59KSJdLAogICJtYXBwaW5ncyI6ICI7QUFBeVcsU0FBUyxvQkFBb0I7QUFDdFksT0FBTyxXQUFXO0FBQ2xCLE9BQU8sVUFBVTtBQUZqQixJQUFNLG1DQUFtQztBQUl6QyxJQUFPLHNCQUFRLGFBQWE7QUFBQSxFQUMxQixTQUFTLENBQUMsTUFBTSxDQUFDO0FBQUEsRUFDakIsU0FBUztBQUFBLElBQ1AsWUFBWSxDQUFDLFFBQVEsT0FBTyxRQUFRLE9BQU8sT0FBTztBQUFBLElBQ2xELE9BQU87QUFBQSxNQUNMLEtBQUssS0FBSyxRQUFRLGtDQUFXLEdBQUc7QUFBQSxNQUNoQyxnQkFBZ0IsS0FBSyxRQUFRLGtDQUFXLGNBQWM7QUFBQSxNQUN0RCxTQUFTLEtBQUssUUFBUSxrQ0FBVyxPQUFPO0FBQUEsTUFDeEMsV0FBVyxLQUFLLFFBQVEsa0NBQVcsU0FBUztBQUFBLElBQzlDO0FBQUEsRUFDRjtBQUFBLEVBQ0EsTUFBTTtBQUFBLEVBQ04sT0FBTztBQUFBLElBQ0wsUUFBUTtBQUFBLElBQ1IsYUFBYTtBQUFBLElBQ2IsZUFBZTtBQUFBLE1BQ2IsT0FBTztBQUFBLE1BQ1AsUUFBUTtBQUFBLFFBQ04sUUFBUTtBQUFBLFFBQ1IsZ0JBQWdCO0FBQUEsUUFDaEIsZ0JBQWdCO0FBQUEsTUFDbEI7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUFBLEVBQ0EsUUFBUTtBQUFBLElBQ04sTUFBTTtBQUFBLElBQ04sS0FBSztBQUFBLEVBQ1A7QUFDRixDQUFDOyIsCiAgIm5hbWVzIjogW10KfQo=
