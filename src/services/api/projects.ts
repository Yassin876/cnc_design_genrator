import { apiClient } from './client';

export interface Project {
  id: string;
  owner_id: string;
  name: string;
  description?: string;
  type: '2D' | '3D';
  current_version: number;
  status: 'ACTIVE' | 'TRASH';
  file_path?: string;
  is_favorite: boolean;
  is_deleted?: boolean;
  deleted_at?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateProjectRequest {
  name: string;
  description?: string;
  type?: '2D' | '3D';
  file_path?: string;
}

export const projectsApiService = {
  getProjects: async (params?: {
    filter?: 'all' | 'recent' | 'favorites' | 'trash';
    status?: 'ACTIVE' | 'TRASH';
    project_type?: '2D' | '3D';
    favorites_only?: boolean;
    recent_only?: boolean;
    limit?: number;
  }): Promise<Project[]> => {
    const res = await apiClient.get<Project[]>('/projects', { params });
    return res.data;
  },

  getRecentProjects: async (limit: number = 10): Promise<Project[]> => {
    const res = await apiClient.get<Project[]>('/projects', { params: { filter: 'recent', limit } });
    return res.data;
  },

  getFavoriteProjects: async (): Promise<Project[]> => {
    const res = await apiClient.get<Project[]>('/projects', { params: { filter: 'favorites' } });
    return res.data;
  },

  getTrashProjects: async (): Promise<Project[]> => {
    const res = await apiClient.get<Project[]>('/projects', { params: { filter: 'trash' } });
    return res.data;
  },

  createProject: async (data: CreateProjectRequest): Promise<Project> => {
    const res = await apiClient.post<Project>('/projects', data);
    return res.data;
  },

  updateProject: async (
    projectId: string,
    data: { name?: string; description?: string; type?: '2D' | '3D'; is_favorite?: boolean; status?: 'ACTIVE' | 'TRASH'; file_path?: string }
  ): Promise<Project> => {
    const res = await apiClient.patch<Project>(`/projects/${projectId}`, data);
    return res.data;
  },

  toggleFavorite: async (projectId: string): Promise<{ id: string; is_favorite: boolean }> => {
    const res = await apiClient.patch<{ id: string; is_favorite: boolean }>(`/projects/${projectId}/favorite`);
    return res.data;
  },

  moveToTrash: async (projectId: string): Promise<{ message: string; id: string }> => {
    const res = await apiClient.patch<{ message: string; id: string }>(`/projects/${projectId}/trash`);
    return res.data;
  },

  restoreFromTrash: async (projectId: string): Promise<{ message: string; id: string }> => {
    const res = await apiClient.patch<{ message: string; id: string }>(`/projects/${projectId}/restore`);
    return res.data;
  },

  deletePermanently: async (projectId: string): Promise<{ message: string; id: string }> => {
    const res = await apiClient.delete<{ message: string; id: string }>(`/projects/${projectId}`);
    return res.data;
  },

  clearTrash: async (): Promise<{ message: string }> => {
    const res = await apiClient.delete<{ message: string }>('/projects/trash/clear');
    return res.data;
  },

  getProjectMessages: async (projectId: string, designType?: string): Promise<any[]> => {
    const res = await apiClient.get(`/projects/${projectId}/messages`, {
      params: designType ? { design_type: designType } : {}
    });
    return res.data;
  },

  saveProjectMessage: async (
    projectId: string,
    payload: { sender: string; text?: string; attachments?: any[]; design_type?: string }
  ): Promise<any> => {
    const res = await apiClient.post(`/projects/${projectId}/messages`, payload);
    return res.data;
  }
};
