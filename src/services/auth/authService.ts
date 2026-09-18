import { authApiService } from '../api/auth';
import { authStorage } from '../api/authStorage';
import { User } from '../../types';

export const authService = {
  async login(email: string, password: string): Promise<User> {
    const res = await authApiService.login(email, password);
    return {
      id: res.user.id,
      name: res.user.name,
      email: res.user.email,
      token: res.access_token,
      created_at: res.user.created_at
    };
  },

  async signup(name: string, email: string, password: string, confirmPassword?: string) {
    return await authApiService.register(name, email, password, confirmPassword);
  },

  async verifyOtp(email: string, otp: string, purpose: 'registration' | 'password_reset' = 'registration') {
    return await authApiService.verifyOtp(email, otp, purpose);
  },

  async resendOtp(email: string, purpose: 'registration' | 'password_reset' = 'registration') {
    return await authApiService.resendOtp(email, purpose);
  },

  async forgotPassword(email: string) {
    return await authApiService.forgotPassword(email);
  },

  async resetPassword(email: string, otp: string, newPassword: string, confirmPassword?: string) {
    return await authApiService.resetPassword(email, otp, newPassword, confirmPassword);
  },

  /**
   * Google OAuth via Electron loopback:
   * 1. Calls window.electronAPI.googleLogin() → opens system browser, catches callback
   * 2. Sends { code, redirect_uri } to the backend POST /auth/google
   * 3. Returns the logged-in User on success
   */
  async googleLogin(): Promise<User> {
    const electronAPI = (window as any).electronAPI;
    if (!electronAPI?.googleLogin) {
      throw new Error('Google login is only available in the Electron desktop app.');
    }

    const result = await electronAPI.googleLogin();
    if (result?.error) {
      throw new Error(result.error);
    }
    if (!result?.code || !result?.redirect_uri) {
      throw new Error('Google login failed: no authorization code returned.');
    }

    const res = await authApiService.googleLogin(result.code, result.redirect_uri);
    return {
      id: res.user.id,
      name: res.user.name,
      email: res.user.email,
      token: res.access_token,
      created_at: res.user.created_at
    };
  },

  logout(): void {
    authApiService.logout();
  },

  getCurrentUser(): User | null {
    return authStorage.getSavedUser();
  },

  async restoreSession(): Promise<User | null> {
    try {
      // First check if we have a valid stored session
      const storedUser = authStorage.getSavedUser();
      const storedToken = authStorage.getAccessToken();
      
      if (storedUser && storedToken) {
        // Validate the token by calling /me
        try {
          const validatedUser = await authApiService.getCurrentUser();
          return validatedUser;
        } catch (err) {
          // Token invalid, clear and return null
          authStorage.clearSession();
          return null;
        }
      }
      
      // No stored session
      return null;
    } catch {
      return null;
    }
  }
};
