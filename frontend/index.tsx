import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './src/App';
import { GameProvider } from './src/contexts/GameContext';
import { AuthProvider } from './src/contexts/AuthContext';
import './src/index.css';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error("Could not find root element to mount to");
}


const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <AuthProvider>
      <GameProvider>
        <App />
      </GameProvider>
    </AuthProvider>
  </React.StrictMode>
);