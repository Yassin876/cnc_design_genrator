import { create } from 'zustand';
import { User } from '../../types';
import { authService } from '../../services/auth/authService';
import { useProjectStore } from './useProjectStore';
import { useWorkspaceStore } from './useWorkspaceStore';
import { use2DWorkspaceStore } from './use2DWorkspaceStore';
import { use3DWorkspaceStore } from './use3DWorkspaceStore';
import { useAiStore } from './useAiStore';

export const cleanupAllClientStores = () => {
  try {
    useProjectStore.getState().setProjects([]);
    useProjectStore.getState().setActiveProject(null);
  } catch (e) {
    console.warn('Error clearing project store:', e);
  }

  try {
    const ws = useWorkspaceStore.getState();
    ws.setActiveProjectId(null, null);
    ws.setDxfContent(null);
    ws.setInspectionData(null);
    ws.setDxfEntities(null);
    ws.setValidationReport(null);
    ws.setProjectVersions([]);
    ws.clearAttachments();
  } catch (e) {
    console.warn('Error clearing workspace store:', e);
  }

  try {
    use2DWorkspaceStore.getState().resetWorkspace();
  } catch (e) {
    console.warn('Error resetting 2D workspace:', e);
  }

  try {
    use3DWorkspaceStore.getState().resetWorkspace();
  } catch (e) {
    console.warn('Error resetting 3D workspace:', e);
  }

  try {
    useAiStore.getState().resetAiState();
  } catch (e) {
    console.warn('Error resetting AI state:', e);
  }
};

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isAuthenticating: boolean; // Prevent duplicate auth requests
  setUser: (user: User | null) => void;
  logout: () => void;
  initializeAuth: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null, // Start with null - will check storage on mount
  isAuthenticated: false,
  isAuthenticating: false,

  setUser: (newUser) => {
    const prevUser = get().user;
    if (!newUser || (prevUser && prevUser.id !== newUser.id)) {
      cleanupAllClientStores();
    }
    set({ user: newUser, isAuthenticated: !!newUser, isAuthenticating: false });
    if (newUser) {
      useProjectStore.getState().fetchProjects(newUser.id);
    }
  },

  logout: () => {
    cleanupAllClientStores();
    authService.logout();
    set({ user: null, isAuthenticated: false, isAuthenticating: false });
  },

  initializeAuth: async () => {
    // Prevent duplicate auth requests
    if (get().isAuthenticating) {
      console.log('[Auth] Auth already in progress, skipping duplicate request');
      return get().isAuthenticated;
    }
    
    set({ isAuthenticating: true });
    
    try {
      // First check if we have a valid session in storage
      const storedUser = authService.getCurrentUser();
      if (storedUser) {
        set({ user: storedUser, isAuthenticated: true, isAuthenticating: false });
        useProjectStore.getState().fetchProjects(storedUser.id);
        return true;
      }
      
      // If no stored user, try to restore from backend
      const user = await authService.restoreSession();
      if (user) {
        set({ user, isAuthenticated: true, isAuthenticating: false });
        useProjectStore.getState().fetchProjects(user.id);
        return true;
      } else {
        cleanupAllClientStores();
        set({ user: null, isAuthenticated: false, isAuthenticating: false });
        return false;
      }
    } catch (error) {
      console.error('[Auth] Auth initialization failed:', error);
      cleanupAllClientStores();
      set({ user: null, isAuthenticated: false, isAuthenticating: false });
      return false;
    }
  }
}));
