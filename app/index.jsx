import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';



// Add browser globals for linter
const { document } = globalThis;

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
