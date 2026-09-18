import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// Startup timing
const startupStart = performance.now();
console.log('[Startup] main.tsx loaded at', startupStart);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <App />
);

const renderTime = performance.now();
console.log('[Startup] React render called at', renderTime, `(took ${renderTime - startupStart}ms)`);
