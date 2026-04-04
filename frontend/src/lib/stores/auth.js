import { writable } from 'svelte/store';
import { api } from '$lib/utils/api';
import { goto } from '$app/navigation';

function createAuthStore() {
  const { subscribe, set, update } = writable({
    isAuthenticated: false,
    user: null,
    token: null,
    loading: true
  });

  return {
    subscribe,
    login: async (email, password) => {
      const formData = new URLSearchParams();
      // OAuth2PasswordRequestForm espera 'username'
      formData.append('username', email);
      formData.append('password', password);

      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/token`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Credenciales inválidas' }));
        throw new Error(err.detail || 'Error en autenticación');
      }

      const { access_token } = await response.json();
      localStorage.setItem('token', access_token);
      
      try {
        const user = await api.get('/users/me/');
        set({ isAuthenticated: true, user, token: access_token, loading: false });
        await goto('/dashboard');
      } catch (e) {
        localStorage.removeItem('token');
        throw new Error('Error al cargar perfil de usuario');
      }
    },
    logout: () => {
      localStorage.removeItem('token');
      set({ isAuthenticated: false, user: null, token: null, loading: false });
      goto('/login');
    },
    checkAuth: async () => {
      if (typeof window === 'undefined') return;
      const token = localStorage.getItem('token');
      if (!token) {
        set({ isAuthenticated: false, user: null, token: null, loading: false });
        return;
      }
      try {
        const user = await api.get('/users/me/');
        set({ isAuthenticated: true, user, token, loading: false });
      } catch (e) {
        localStorage.removeItem('token');
        set({ isAuthenticated: false, user: null, token: null, loading: false });
      }
    }
  };
}

export const auth = createAuthStore();

export const login = (email, password) => auth.login(email, password);
export const logout = () => auth.logout();
export const checkAuth = () => auth.checkAuth();
