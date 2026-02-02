import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { message } from 'antd';
import api, { getAuthUrl, setAuthToken } from '../api/client';
import { BACKEND_URL } from '../config';
import type { User } from '../types';

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  loginLoading: boolean;
  login: () => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const TOKEN_KEY = 'access_token';
const USER_KEY = 'user';

function readTokenFromUrlOrStorage(): string | null {
  const params = new URLSearchParams(window.location.search);
  const urlToken = params.get('token');
  if (urlToken) return urlToken;
  return sessionStorage.getItem(TOKEN_KEY);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    try {
      const s = sessionStorage.getItem(USER_KEY);
      return s ? JSON.parse(s) : null;
    } catch {
      return null;
    }
  });
  const [token, setTokenState] = useState<string | null>(readTokenFromUrlOrStorage);
  const [loading, setLoading] = useState(true);
  const [loginLoading, setLoginLoading] = useState(false);

  const setToken = useCallback((t: string | null) => {
    setTokenState(t);
    if (t) sessionStorage.setItem(TOKEN_KEY, t);
    else sessionStorage.removeItem(TOKEN_KEY);
    setAuthToken(t);
  }, []);

  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  // Strip ?token= / ?error= from URL after reading (OAuth redirect)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get('token');
    const error = params.get('error');
    if (error) {
      console.error('Auth error:', error);
    }
    if (urlToken || error) {
      window.history.replaceState({}, '', window.location.pathname);
    }
    if (urlToken) setToken(urlToken);
  }, [setToken]);

  // Fetch user when token exists
  useEffect(() => {
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    api.get<User>('/auth/me')
      .then(({ data }) => {
        const u: User = {
          email: data.email,
          name: data.name,
          picture: data.picture,
          role: data.role,
          is_active: data.is_active,
          permissions: data.permissions,
        };
        setUser(u);
        sessionStorage.setItem(USER_KEY, JSON.stringify(u));
      })
      .catch(() => {
        setToken(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, [token, setToken]);

  const login = useCallback(async () => {
    setLoginLoading(true);
    try {
      const { auth_url } = await getAuthUrl();
      if (auth_url) {
        window.location.href = auth_url;
      } else {
        message.error('El backend no devolvió la URL de login. Revisa la configuración.');
      }
    } catch (err: unknown) {
      const axiosErr = err && typeof err === 'object' && 'response' in err ? (err as { response?: { status?: number; data?: unknown } }) : null;
      const status = axiosErr?.response?.status;
      const detail = axiosErr?.response?.data && typeof axiosErr.response.data === 'object' && axiosErr.response.data !== null && 'detail' in axiosErr.response.data
        ? String((axiosErr.response.data as { detail: unknown }).detail)
        : null;
      if (status === 404 || (err && typeof err === 'object' && 'message' in err && String((err as Error).message).includes('Network Error'))) {
        message.error(
          `No se pudo conectar al backend (${BACKEND_URL}). ¿Está en marcha? Abre la consola del navegador (F12) para más detalles.`
        );
      } else if (detail) {
        message.error(detail);
      } else {
        message.error(err instanceof Error ? err.message : 'Error al obtener la URL de login. Revisa que el backend esté en marcha.');
      }
    } finally {
      setLoginLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    sessionStorage.removeItem(USER_KEY);
  }, [setToken]);

  const value: AuthContextValue = {
    user,
    token,
    loading,
    loginLoading,
    login,
    logout,
    isAuthenticated: !!token && !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
