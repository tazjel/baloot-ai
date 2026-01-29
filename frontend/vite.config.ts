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
        '/react-py4web': {
          target: 'http://127.0.0.1:3005',
          changeOrigin: true,
          secure: false,
          bypass: (req) => {
            // Bypass proxy for the app's static assets and index.html
            // The app is served at /react-py4web/static/build/
            if (req.url.startsWith('/react-py4web/static/build/') ||
              req.url.includes('/src/') ||
              req.url.includes('/@vite/') ||
              req.url.includes('/node_modules/')) {
              return req.url;
            }
          },
        },
        '/static': {
          target: 'http://127.0.0.1:3005',
          changeOrigin: true,
          secure: false,
        },
        '/user': 'http://127.0.0.1:3005',
        '/signup': 'http://127.0.0.1:3005',
        '/signin': 'http://127.0.0.1:3005',
        '/save_score': 'http://127.0.0.1:3005',
        '/leaderboard': 'http://127.0.0.1:3005',
        '/training_data': 'http://127.0.0.1:3005',
        '/submit_training': 'http://127.0.0.1:3005',
        '/brain': 'http://127.0.0.1:3005',
        '/analyze_screenshot': 'http://127.0.0.1:3005',
        '/ask_strategy': 'http://127.0.0.1:3005',
        '/generate_scenario': 'http://127.0.0.1:3005',
        '/analyze_match': 'http://127.0.0.1:3005',
        '/ai_thoughts': 'http://127.0.0.1:3005',
        '/match_history': 'http://127.0.0.1:3005',
        '/replay': 'http://127.0.0.1:3005',
        '/puzzles': 'http://127.0.0.1:3005',
      },
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
