import { User } from '../../types';

const ACCESS_TOKEN_KEY = 'cnc_access_token';
const REFRESH_TOKEN_KEY = 'cnc_refresh_token';
const USER_KEY = 'cnc_auth_user';

export interface StoredSession {
  accessToken: string;
  refreshToken: string;
  user: User;
}

export const authStorage = {
  saveSession(accessToken: string, refreshToken: string, user: User): void {
    try {
      localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch (e) {
      console.error('Failed to store authentication tokens in desktop secure storage', e);
    }
  },

  saveUser(user: User): void {
    try {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch (e) {
      console.error('Failed to save user in desktop storage', e);
    }
  },


  getAccessToken(): string | null {
    try {
      return localStorage.getItem(ACCESS_TOKEN_KEY);
    } catch {
      return null;
    }
  },

  getRefreshToken(): string | null {
    try {
      return localStorage.getItem(REFRESH_TOKEN_KEY);
    } catch {
      return null;
    }
  },

  getSavedUser(): User | null {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  clearSession(): void {
    try {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    } catch (e) {
      console.error('Failed to clear desktop auth storage', e);
    }
  }
};
