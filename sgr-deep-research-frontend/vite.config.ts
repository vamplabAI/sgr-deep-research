import { fileURLToPath, URL } from 'node:url'
import { dirname } from 'node:path'
import * as path from 'path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// Create plugins array
const plugins = [vue(), vueJsx()]

// Vue DevTools only in development mode
// Temporarily disabled due to localStorage issues in Node.js environment
// Uncomment and configure if needed:
// if (process.env.NODE_ENV === 'development' || process.env.DEV) {
//   const vueDevTools = (await import('vite-plugin-vue-devtools')).default
//   plugins.push(vueDevTools())
// }

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const backendUrl = process.env.VITE_API_BASE_URL || 'http://localhost:8010'

  return {
    plugins,
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        '@app': path.resolve(__dirname, './src/app/'),
        '@pages': path.resolve(__dirname, './src/pages/'),
        '@widgets': path.resolve(__dirname, './src/widgets/'),
        '@features': path.resolve(__dirname, './src/features/'),
        '@entities': path.resolve(__dirname, './src/entities/'),
        '@shared': path.resolve(__dirname, './src/shared/'),
      },
    },
    server: {
      host: true,
      proxy: {
        // Proxy API requests to backend to avoid CORS issues in development
        '/health': {
          target: backendUrl,
          changeOrigin: true,
        },
        '/agents': {
          target: backendUrl,
          changeOrigin: true,
        },
        '/v1': {
          target: backendUrl,
          changeOrigin: true,
        },
      },
    },
    css: {
      preprocessorOptions: {
        scss: {
          silenceDeprecations: ['legacy-js-api'], // silence Dart-sass warnings
          additionalData: `
        @use '/src/app/assets/styles/breakpoints.scss' as breakpoints;
        @use '/src/app/assets/styles/responsive.scss' as responsive;
        @use '/src/app/assets/styles/typography.scss' as typography;
        `,
        },
      },
    },
  }
})
