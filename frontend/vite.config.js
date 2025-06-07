import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
    sourcemap: true, // Enable sourcemaps to help with debugging
    minify: true,
    commonjsOptions: {
      // Helps with circular dependencies
      transformMixedEsModules: true
    },
    rollupOptions: {
      treeshake: {
        moduleSideEffects: true,
        propertyReadSideEffects: true,
        tryCatchDeoptimization: true,
        unknownGlobalSideEffects: true,
      },
      output: {
        manualChunks: (id) => {
          // Group react packages together
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) {
            return 'vendor-react';
          }
          // Group UI libraries together
          if (id.includes('node_modules/flowbite') || id.includes('node_modules/lucide-react')) {
            return 'vendor-ui';
          }
        },
        // Ensure proper hoisting of variables to avoid initialization errors
        hoistTransitiveImports: true,
        // Use a deterministic chunk naming strategy
        chunkFileNames: 'assets/[name]-[hash].js',
        // Ensure proper ordering of modules
        inlineDynamicImports: false
      }
    }
  },
  server: {
    port: 3200,
    host: '0.0.0.0',
    open: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8200',
        changeOrigin: true
      }
    }
  }
})
