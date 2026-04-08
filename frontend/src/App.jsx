import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// TODO: reconstruir vistas aquí
function Placeholder({ name }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <p className="text-on-surface font-body text-sm opacity-60">{name}</p>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Placeholder name="Login" />} />
        <Route path="/dashboard" element={<Placeholder name="Dashboard" />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
