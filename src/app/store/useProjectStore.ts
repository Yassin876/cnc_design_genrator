import { create } from 'zustand';
import { Project, GenerationJob } from '../../types';
import { projectService } from '../../services/projects/projectService';

interface ProjectState {
  projects: Project[];
  activeProject: Project | null;
  jobs: GenerationJob[];
  isLoading: boolean;
  setProjects: (projects: Project[]) => void;
  setActiveProject: (project: Project | null) => void;
  fetchProjects: (userId?: string) => Promise<void>;
  fetchJobs: (userId?: string) => Promise<void>;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  activeProject: null,
  jobs: [],
  isLoading: false,
  setProjects: (projects) => set({ projects }),
  setActiveProject: (activeProject) => set({ activeProject }),
  fetchProjects: async (userId?: string) => {
    set({ isLoading: true });
    try {
      const data = await projectService.fetchProjects();
      set({ projects: data });
      if (data.length > 0 && !get().activeProject) {
        set({ activeProject: data[0] });
      } else if (data.length === 0) {
        set({ activeProject: null });
      }
    } catch (err) {
      console.error('Failed to load projects', err);
      set({ projects: [], activeProject: null });
    } finally {
      set({ isLoading: false });
    }
  },
  fetchJobs: async (userId?: string) => {
    set({ jobs: [] });
  }
}));

