import { w as writable } from "./index.js";
import { a as api } from "./api.js";
import "clsx";
import "@sveltejs/kit/internal";
import "./url.js";
import "./utils.js";
import "@sveltejs/kit/internal/server";
import "./root.js";
import "./exports.js";
import "./state.svelte.js";
function goto(url, opts = {}) {
  {
    throw new Error("Cannot call goto(...) on the server");
  }
}
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
      formData.append("username", email);
      formData.append("password", password);
      const baseUrl = "http://localhost:8000";
      const response = await fetch(`${baseUrl}/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded"
        },
        body: formData
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Credenciales inválidas" }));
        throw new Error(err.detail || "Error en autenticación");
      }
      const { access_token } = await response.json();
      localStorage.setItem("token", access_token);
      try {
        const user = await api.get("/users/me/");
        set({ isAuthenticated: true, user, token: access_token, loading: false });
        await goto("/dashboard");
      } catch (e) {
        localStorage.removeItem("token");
        throw new Error("Error al cargar perfil de usuario");
      }
    },
    logout: () => {
      localStorage.removeItem("token");
      set({ isAuthenticated: false, user: null, token: null, loading: false });
      goto();
    },
    checkAuth: async () => {
      if (typeof window === "undefined") return;
      const token = localStorage.getItem("token");
      if (!token) {
        set({ isAuthenticated: false, user: null, token: null, loading: false });
        return;
      }
      try {
        const user = await api.get("/users/me/");
        set({ isAuthenticated: true, user, token, loading: false });
      } catch (e) {
        localStorage.removeItem("token");
        set({ isAuthenticated: false, user: null, token: null, loading: false });
      }
    }
  };
}
const auth = createAuthStore();
export {
  auth as a,
  goto as g
};
