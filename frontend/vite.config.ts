import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  return {
    server: {
      port: 3000,
      host: '0.0.0.0',
      proxy: {
        '/socket.io': {
          target: 'http://127.0.0.1:3005',
          ws: true
        },
        '/user': 'http://127.0.0.1:8000', // Still 8000 for Auth? No, we are using 3002 for everything game related now.
        // Actually, existing auth might be on Py4Web (8000). Game Server (3002).
        // Let's proxy socket.io to 3002.
        // Add other endpoints as needed or use a wildcard if possible/safe, 
        // but explicit is better for now given the controller structure.
        // py4web controllers often map to /{appname}/{function} or just /{function} for _default
        // Assuming _default or root mapping based on controllers.py
      }
    },
    plugins: [react()],
    base: '/react-py4web/static/build/',
    build: {
      outDir: '../static/build',
      emptyOutDir: true
    },
    define: {
      'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
      'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY)
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      }
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/setupTests.ts',
    }
  };
});
