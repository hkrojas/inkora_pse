  // Ruta: frontend/src/components/ThemeToggle.jsx
  import React from 'react';
  import { Moon, Sun } from 'lucide-react';
  import { useTheme } from '../context/ThemeContext.jsx';

  const ThemeToggle = () => {
    const { theme, toggleTheme } = useTheme();

    return (
      <button
        onClick={toggleTheme}
        className="p-2 rounded-xl bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-300 hover:bg-surface-200 dark:hover:bg-surface-700 transition-colors flex items-center justify-center"
        title="Alternar tema"
      >
        {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
      </button>
    );
  };

  export default ThemeToggle;