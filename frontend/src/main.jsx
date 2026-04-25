import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './app.css';
import './styles/tokens.css';
import './styles/globals.css';
import App from './App.jsx';
import { ThemeProvider } from './context/ThemeContext';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>
);
