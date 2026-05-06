import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { BASE_URL } from '../lib/utils/config';

const AuthContext = createContext(null);
const TOKEN_KEY = 'token';

function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
}

function clearStoredToken() {
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
}

function storeToken(token, remember) {
  clearStoredToken();
  const storage = remember ? localStorage : sessionStorage;
  storage.setItem(TOKEN_KEY, token);
}

function getApiErrorMessage(detail, fallback) {
  if (typeof detail === 'string') return detail;
  if (detail?.message) return detail.message;
  return fallback;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async (token) => {
    try {
      const res = await fetch(`${BASE_URL}/users/me/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('unauthorized');
      const data = await res.json();
      setUser(data);
      return data;
    } catch {
      clearStoredToken();
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    const token = getStoredToken();
    if (token) {
      fetchMe(token).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [fetchMe]);

  const login = async (email, password, options = {}) => {
    const form = new URLSearchParams();
    form.append('username', email);
    form.append('password', password);
    form.append('grant_type', 'password');

    const res = await fetch(`${BASE_URL}/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(getApiErrorMessage(err.detail, 'Credenciales invalidas'));
    }
    const { access_token } = await res.json();
    storeToken(access_token, Boolean(options.remember));
    return fetchMe(access_token);
  };

  const logout = () => {
    clearStoredToken();
    setUser(null);
  };

  const refreshUser = async () => {
    const token = getStoredToken();
    if (token) await fetchMe(token);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
