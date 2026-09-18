import { apiClient } from './client';
import { authStorage } from './authStorage';
import { User } from '../../types';

export interface AuthErrorResponse {
  success: boolean;
  message: string;
  code: string;
}

export class AuthCustomError extends Error {
  code: string;

  constructor(message: string, code: string) {
    super(message);
    this.name = 'AuthCustomError';
    this.code = code;
  }
}

export interface RegisterResponse {
  success: boolean;
  message: string;
  email: string;
  require_verification: boolean;
}


export interface TokenResponse {
  success: boolean;
  message: string;
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: {
    id: string;
    name: string;
    email: string;
    is_email_verified: boolean;
    is_active: boolean;
    created_at?: string;
  };
}

export interface GenericAuthResponse {
  success: boolean;
  message: string;
}



function handleAxiosAuthError(err: any): never {
  if (err.response && err.response.data) {
    const data = err.response.data;
    const message = data.message || data.detail || 'Authentication request failed.';
    const code = data.code || (err.response.status === 401 ? 'AUTH_UNAUTHORIZED' : 'AUTH_ERROR');
    throw new AuthCustomError(message, code);
  }
  if (err.code === 'ECONNABORTED' || err.message?.includes('Network Error')) {
    throw new AuthCustomError('Backend auth service unavailable. Please check backend status.', 'BACKEND_UNAVAILABLE');
  }
  throw new AuthCustomError(err.message || 'An unexpected error occurred.', 'UNKNOWN_ERROR');
}

export const authApiService = {
  async register(name: string, email: string, password: string, confirmPassword?: string): Promise<RegisterResponse> {
    try {
      const res = await apiClient.post<RegisterResponse>('/auth/register', {
        name,
        email,
        password,
        confirm_password: confirmPassword || password
      });
      return res.data;
    } catch (err: any) {
      handleAxiosAuthError(err);
    }
  },

  async verifyOtp(email: string, otp: string, purpose: 'registration' | 'password_reset' = 'registration'): Promise<TokenResponse | GenericAuthResponse> {
    try {
      const res = await apiClient.post<TokenResponse>('/auth/verify-otp', {
        email,
        otp,
        purpose
      });

      if (res.data.access_token && res.data.user) {
        const user: User = {
          id: res.data.user.id,
          name: res.data.user.name,
          email: res.data.user.email,
          token: res.data.access_token,
          created_at: res.data.user.created_at
        };
        authStorage.saveSession(res.data.access_token, res.data.refresh_token, user);
      }

      return res.data;
    } catch (err: any) {
      handleAxiosAuthError(err);
    }
  },

  async resendOtp(email: string, purpose: 'registration' | 'password_reset' = 'registration'): Promise<GenericAuthResponse> {
    try {
      const res = await apiClient.post<GenericAuthResponse>('/auth/resend-otp', {
        email,
        purpose
      });
      return res.data;
    } catch (err: any) {
      handleAxiosAuthError(err);
    }
  },

  async login(email: string, password: string): Promise<TokenResponse> {
    try {
      const res = await apiClient.post<TokenResponse>('/auth/login', {
        email,
        password
      });

      if (res.data.access_token && res.data.user) {
        const user: User = {
          id: res.data.user.id,
          name: res.data.user.name,
          email: res.data.user.email,
          token: res.data.access_token,
          created_at: res.data.user.created_at
        };
        authStorage.saveSession(res.data.access_token, res.data.refresh_token, user);
      }

      return res.data;
    } catch (err: any) {
      handleAxiosAuthError(err);
    }
  },

  async forgotPassword(email: string): Promise<GenericAuthResponse> {
    try {
      const res = await apiClient.post<GenericAuthResponse>('/auth/forgot-password', { email });
      return res.data;
    } catch (err: any) {
      handleAxiosAuthError(err);
    }
  },

  async resetPassword(email: string, otp: string, newPassword: string, confirmPassword?: string): Promise<GenericAuthResponse> {
    try {
      const res = await apiClient.post<GenericAuthResponse>('/auth/reset-password', {
        email,
        otp,
        new_password: newPassword,
        confirm_password: confirmPassword || newPassword
      });
      return res.data;
    } catch (err: any) {
      handleAxiosAuthError(err);
    }
  },

  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    try {
      const res = await apiClient.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken });
      if (res.data.access_token && res.data.user) {
        const user: User = {
          id: res.data.user.id,
          name: res.data.user.name,
          email: res.data.user.email,
          token: res.data.access_token,
          created_at: res.data.user.created_at
        };
        authStorage.saveSession(res.data.access_token, res.data.refresh_token, user);
      }
      return res.data;
    } catch (err: any) {
      handleAxiosAuthError(err);
    }
  },

  async getCurrentUser(): Promise<User> {
    const token = authStorage.getAccessToken();
    if (!token) {
      throw new AuthCustomError('No access token available', 'AUTH_UNAUTHORIZED');
    }

    try {
      const res = await apiClient.get('/auth/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = res.data;
      const user: User = {
        id: data.id,
        name: data.name,
        email: data.email,
        avatar_url: data.avatar_url || authStorage.getSavedUser()?.avatar_url || (typeof localStorage !== 'undefined' ? localStorage.getItem('ANTI_DESIGN_AVATAR') : null) || undefined,
        token: token,
        created_at: data.created_at
      };
      return user;
    } catch (err: any) {
      // If token is invalid, clear session and return null (don't try refresh here)
      authStorage.clearSession();
      throw new AuthCustomError('Session expired', 'AUTH_SESSION_EXPIRED');
    }
  },

  async updateProfile(name?: string, avatarUrl?: string): Promise<User> {
    try {
      const payload: any = {};
      if (name !== undefined) payload.name = name;
      if (avatarUrl !== undefined) payload.avatar_url = avatarUrl;
      const res = await apiClient.put('/auth/profile', payload);
      const data = res.data;
      const user: User = {
        id: data.id,
        name: data.name,
        email: data.email,
        avatar_url: data.avatar_url || avatarUrl || undefined,
        token: authStorage.getAccessToken() || '',
        created_at: data.created_at
      };
      authStorage.saveUser(user);
      if (user.avatar_url && typeof localStorage !== 'undefined') {
        localStorage.setItem('ANTI_DESIGN_AVATAR', user.avatar_url);
      }
      return user;
    } catch (err: any) {
      handleAxiosAuthError(err);
    }
  },

  async updateAvatar(avatarUrl: string): Promise<User> {
    return this.updateProfile(undefined, avatarUrl);
  },

  async changePassword(currentPassword: string, newPassword: string, confirmPassword?: string): Promise<GenericAuthResponse> {
    try {
      const res = await apiClient.post<GenericAuthResponse>('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword || newPassword
      });
      return res.data;
    } catch (err: any) {
      handleAxiosAuthError(err);
    }
  },

  async requestEmailChange(currentPassword: string, newEmail: string): Promise<GenericAuthResponse> {
    try {
      const res = await apiClient.post<GenericAuthResponse>('/auth/request-email-change', {
        current_password: currentPassword,
        new_email: newEmail
      });
      return res.data;
    } catch (err: any) {
      handleAxiosAuthError(err);
    }
  },

  async verifyEmailChange(newEmail: string, otp: string): Promise<TokenResponse> {
    try {
      const res = await apiClient.post<TokenResponse>('/auth/verify-email-change', {
        new_email: newEmail,
        otp
      });
      if (res.data.access_token && res.data.user) {
        const user: User = {
          id: res.data.user.id,
          name: res.data.user.name,
          email: res.data.user.email,
          token: res.data.access_token,
          created_at: res.data.user.created_at
        };
        authStorage.saveSession(res.data.access_token, res.data.refresh_token, user);
      }
      return res.data;
    } catch (err: any) {
      handleAxiosAuthError(err);
    }
  },

  logout(): void {
    authStorage.clearSession();
  },

  async googleLogin(code: string, redirectUri: string): Promise<TokenResponse> {
    try {
      const res = await apiClient.post<TokenResponse>('/auth/google', {
        code,
        redirect_uri: redirectUri
      });
      if (res.data.access_token && res.data.user) {
        const user: User = {
          id: res.data.user.id,
          name: res.data.user.name,
          email: res.data.user.email,
          token: res.data.access_token,
          created_at: res.data.user.created_at
        };
        authStorage.saveSession(res.data.access_token, res.data.refresh_token, user);
      }
      return res.data;
    } catch (err: any) {
      handleAxiosAuthError(err);
    }
  }
};

