import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

const isPublicLanding = ['/', '/presentacion'].includes(window.location.pathname);
const root = createRoot(document.getElementById('root'));

async function bootstrap() {
  if (isPublicLanding) {
    const { default: PublicLandingApp } = await import('./PublicLandingApp.jsx');
    root.render(
      <StrictMode>
        <PublicLandingApp />
      </StrictMode>,
    );
    return;
  }

  await Promise.all([
    import('./app.css'),
    import('./styles/tokens.css'),
    import('./styles/globals.css'),
  ]);
  await import('./styles/operations-redesign.css');
  const [{ default: App }, { ThemeProvider }] = await Promise.all([
    import('./App.jsx'),
    import('./context/ThemeContext'),
  ]);

  root.render(
    <StrictMode>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </StrictMode>,
  );
}

bootstrap();
