/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Edition configuration for build-time code exclusion
const edition = process.env.VITE_EDITION || 'pro'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  define: {
    // Make edition available as global constant for tree-shaking
    '__EDITION__': JSON.stringify(edition),
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    // Required for Docker: use polling instead of native file watching
    watch: {
      usePolling: true,
      interval: 100
    }
  },
  // ADCL: Configuration is Code - Document tooling decisions
  // Treat all .js files as JSX for developer convenience
  // Rationale: Reduces cognitive load, zero performance impact, build output identical
  // Tooling should be liberal in what it accepts (Unix philosophy)
  esbuild: {
    loader: 'jsx',
    include: /src\/.*\.jsx?$/,
    exclude: []
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        '.js': 'jsx'
      }
    }
  }
})
