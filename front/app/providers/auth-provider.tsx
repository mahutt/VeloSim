/**
 * MIT License
 *
 * Copyright (c) 2025 VeloSim Contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

import React, {
  createContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { useNavigate } from 'react-router';
import api from '~/api';
import { TOKEN_STORAGE_KEY } from '~/constants';
import type { User } from '~/types';

export interface AuthState {
  user: User | null;
  setUser: React.Dispatch<React.SetStateAction<User | null>>;
  loading: boolean;
  setLoading: React.Dispatch<React.SetStateAction<boolean>>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  setToken: (token: string) => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

const setAuthCookie = (token: string) => {
  // Set cookie with appropriate settings
  // SameSite=Lax allows cookie to be sent with WebSocket from same site
  document.cookie = `access_token=${token}; path=/; SameSite=Lax; Secure=${window.location.protocol === 'https:'}`;
};

const removeAuthCookie = () => {
  document.cookie =
    'access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
};

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const setToken = (newToken: string) => {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, newToken);
    setAuthCookie(newToken);
  };

  const refreshUser = async () => {
    setLoading(true);
    try {
      const response = await api.get<User>('/users/me');
      setUser(response.data);
    } catch {
      setUser(null);
    }
    setLoading(false);
  };

  useEffect(() => {
    const storedToken =
      typeof window !== 'undefined'
        ? sessionStorage.getItem(TOKEN_STORAGE_KEY)
        : null;

    if (storedToken) {
      setAuthCookie(storedToken);
      refreshUser();
    } else {
      setLoading(false);
    }
  }, []);

  const logout = () => {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    removeAuthCookie();
    setUser(null);
    navigate('/login');
  };

  const value: AuthState = {
    user,
    setUser,
    loading,
    setLoading,
    logout,
    refreshUser,
    setToken,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export { AuthContext };
