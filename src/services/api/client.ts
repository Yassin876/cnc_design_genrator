import axios, { AxiosError, AxiosRequestConfig } from 'axios';
import { useAuthStore } from '../../app/store/useAuthStore';
import { authStorage } from './authStorage';

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000, // 5 minutes for deep learning / Hunyuan3D CAD generation
});

// Refresh request deduplication
let refreshPromise: Promise<string> | null = null;

// Security: Attach Auth JWT / Session Token dynamically
apiClient.interceptors.request.use((config) => {
  const token = authStorage.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor with deduplicated token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean; _skipRefresh?: boolean };

    // If 401 and not already retried and not skipped
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest._skipRefresh) {
      originalRequest._retry = true;

      // If a refresh is already in progress, wait for it
      if (refreshPromise) {
        try {
          const newToken = await refreshPromise;
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
          }
          return apiClient(originalRequest);
        } catch (refreshErr) {
          // Refresh failed, logout
          useAuthStore.getState().logout();
          return Promise.reject(error);
        }
      }

      // Start new refresh
      const refreshToken = authStorage.getRefreshToken();
      
      if (refreshToken) {
        refreshPromise = (async () => {
          try {
            const { authApiService } = await import('./auth');
            const response = await authApiService.refreshToken(refreshToken);
            return response.access_token;
          } catch (err) {
            refreshPromise = null;
            throw err;
          }
        })();

        try {
          const newToken = await refreshPromise;
          refreshPromise = null;
          
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
          }
          return apiClient(originalRequest);
        } catch (refreshErr) {
          refreshPromise = null;
          useAuthStore.getState().logout();
          return Promise.reject(error);
        }
      } else {
        // No refresh token - logout
        useAuthStore.getState().logout();
      }
    }

    return Promise.reject(error);
  }
);

// Security: Path Traversal Protection Helper
export const sanitizeFilePath = (filePath: string): string => {
  if (!filePath) return '';
  // Strip relative path traversal sequences
  return filePath
    .replace(/\.\.[\/\\]/g, '')
    .replace(/[\/\\]\.\./g, '')
    .trim();
};

// Security & File Validation Helpers
export const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024; // 50MB
export const ALLOWED_EXTENSIONS = ['.stl', '.step', '.stp', '.dxf', '.png', '.jpg', '.jpeg', '.obj', '.gcode', '.nc'];

export interface FileValidationResult {
  valid: boolean;
  error?: string;
  filename: string;
}

export const validateFileBeforeUpload = (file: File): FileValidationResult => {
  const filename = file.name.replace(/[^a-zA-Z0-9._-]/g, '_');
  const ext = '.' + filename.split('.').pop()?.toLowerCase();

  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return {
      valid: false,
      error: `Invalid file extension (${ext}). Allowed: ${ALLOWED_EXTENSIONS.join(', ')}`,
      filename
    };
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      valid: false,
      error: `File size (${(file.size / (1024 * 1024)).toFixed(1)}MB) exceeds limit of 50MB.`,
      filename
    };
  }

  return { valid: true, filename };
};

// Retry Wrapper with Exponential Backoff for Robust Error Handling
export async function fetchWithRetry<T>(
  fn: () => Promise<T>,
  maxRetries = 2,
  delayMs = 1000
): Promise<T> {
  let attempt = 0;
  while (attempt <= maxRetries) {
    try {
      return await fn();
    } catch (err) {
      attempt++;
      if (attempt > maxRetries) {
        const errorDetail = (err as AxiosError<{ detail?: string }>)?.response?.data?.detail
          || (err as Error).message
          || 'Backend service request failed.';
        throw new Error(errorDetail);
      }
      await new Promise((resolve) => setTimeout(resolve, delayMs * Math.pow(2, attempt - 1)));
    }
  }
  throw new Error('Maximum retries exceeded');
}

export const getStaticFileUrl = (path: string | undefined): string => {
  if (!path) return '';
  if (path.startsWith('blob:') || path.startsWith('data:') || path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  const cleanPath = sanitizeFilePath(path).replace(/\\/g, '/');

  // Strip leading slash if any for uniform matching
  const normalized = cleanPath.startsWith('/') ? cleanPath.slice(1) : cleanPath;

  if (normalized.startsWith('storage/outputs/') || normalized.includes('/storage/outputs/')) {
    const relativePart = normalized.includes('/storage/outputs/')
      ? normalized.split('/storage/outputs/')[1]
      : normalized.replace('storage/outputs/', '');
    return `http://127.0.0.1:8000/static/outputs/${relativePart}`;
  }

  if (normalized.startsWith('storage/uploads/') || normalized.includes('/storage/uploads/')) {
    const relativePart = normalized.includes('/storage/uploads/')
      ? normalized.split('/storage/uploads/')[1]
      : normalized.replace('storage/uploads/', '');
    return `http://127.0.0.1:8000/static/uploads/${relativePart}`;
  }

  if (normalized.startsWith('static/outputs/') || normalized.includes('/static/outputs/')) {
    const relativePart = normalized.includes('/static/outputs/')
      ? normalized.split('/static/outputs/')[1]
      : normalized.replace('static/outputs/', '');
    return `http://127.0.0.1:8000/static/outputs/${relativePart}`;
  }

  return `http://127.0.0.1:8000/api/v1/files/download?file_path=${encodeURIComponent(cleanPath)}`;
};
