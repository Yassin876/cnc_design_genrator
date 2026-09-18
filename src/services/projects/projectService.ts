import { apiClient, fetchWithRetry } from '../api/client';
import { CNCProjectBundle, Project, ProjectVersion } from '../../types';

export const projectService = {
  async saveProjectFile(bundle: CNCProjectBundle, filePath?: string): Promise<string> {
    let targetPath = filePath || `C:\\Users\\Public\\Projects\\${bundle.metadata.title.toLowerCase().replace(/\s+/g, '_')}.cncproj`;

    if (window.electronAPI?.saveFileDialog && !filePath) {
      const nativePath = await window.electronAPI.saveFileDialog(`${bundle.metadata.title.toLowerCase().replace(/\s+/g, '_')}.cncproj`);
      if (nativePath) targetPath = nativePath;
    }

    try {
      const jsonContent = JSON.stringify(bundle, null, 2);
      await apiClient.post('/projects/save-file', { file_path: targetPath, content: jsonContent });
    } catch (e) {
      console.warn('[ProjectService] Backend save endpoint unavailable, using localStorage fallback');
      localStorage.setItem(`cnc_proj_${bundle.metadata.title}`, JSON.stringify(bundle));
    }

    return targetPath;
  },

  async openProjectFile(filePath?: string): Promise<CNCProjectBundle | null> {
    let targetPath = filePath;

    if (window.electronAPI?.openFileDialog && !targetPath) {
      const nativePath = await window.electronAPI.openFileDialog();
      if (nativePath) targetPath = nativePath;
    }

    if (!targetPath) return null;

    try {
      const res = await apiClient.get(`/files/download?file_path=${encodeURIComponent(targetPath)}`);
      return res.data;
    } catch (e) {
      console.warn('[ProjectService] Backend load endpoint unavailable');
    }

    return null;
  },

  async fetchProjects(): Promise<Project[]> {
    return fetchWithRetry(async () => {
      const res = await apiClient.get('/projects');
      return res.data;
    }).catch(() => []);
  },


  async fetchProjectVersions(projectId: string): Promise<ProjectVersion[]> {
    return fetchWithRetry(async () => {
      const res = await apiClient.get(`/projects/${projectId}/versions`);
      return res.data;
    }).catch(() => []);
  },

  async restoreVersion(projectId: string, versionId: string): Promise<{ status: string; new_version_id: string; message: string }> {
    return fetchWithRetry(async () => {
      const res = await apiClient.post(`/projects/${projectId}/versions/${versionId}/restore`);
      return res.data;
    });
  },

  async duplicateVersion(projectId: string, versionId: string): Promise<{ status: string; new_project_id: string; message: string }> {
    return fetchWithRetry(async () => {
      const res = await apiClient.post(`/projects/${projectId}/versions/${versionId}/duplicate`);
      return res.data;
    });
  }
};
