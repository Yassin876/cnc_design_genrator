import React, { useState, useEffect } from 'react';
import { Search, Hexagon, ArrowUpRight, Star, Trash2, Edit2, Copy, RefreshCw, Plus } from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { projectsApiService, Project } from '../../services/api/projects';
import { ProjectCard } from '../../components/projects/ProjectCard';

const ProjectsView: React.FC = () => {
  const { loadFile, setNewProjectModalOpen } = useWorkspaceStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'All' | '3D' | '2D'>('All');
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState<string>('');

  const fetchProjects = async () => {
    setIsLoading(true);
    try {
      const data = await projectsApiService.getProjects({ status: 'ACTIVE' });
      setProjects(data);
    } catch (err) {
      console.error('Failed to fetch projects', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleToggleFavorite = async (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation();
    // Optimistic UI update
    setProjects((prev) =>
      prev.map((p) => (p.id === projectId ? { ...p, is_favorite: !p.is_favorite } : p))
    );
    try {
      const res = await projectsApiService.toggleFavorite(projectId);
      setProjects((prev) =>
        prev.map((p) => (p.id === projectId ? { ...p, is_favorite: res.is_favorite } : p))
      );
    } catch (err) {
      console.error('Failed to toggle favorite', err);
      fetchProjects();
    }
  };

  const handleMoveToTrash = async (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation();
    // Optimistic UI update: remove from list immediately
    setProjects((prev) => prev.filter((p) => p.id !== projectId));
    try {
      await projectsApiService.moveToTrash(projectId);
    } catch (err) {
      console.error('Failed to move project to trash', err);
      fetchProjects();
    }
  };

  const handleStartRename = (e: React.MouseEvent, p: Project) => {
    e.stopPropagation();
    setEditingProjectId(p.id);
    setEditingName(p.name);
  };

  const handleSaveRename = async (e: React.FormEvent, projectId: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!editingName.trim()) return;
    try {
      const updated = await projectsApiService.updateProject(projectId, { name: editingName.trim() });
      setProjects((prev) => prev.map((p) => (p.id === projectId ? updated : p)));
      setEditingProjectId(null);
    } catch (err) {
      console.error('Failed to rename project', err);
    }
  };

  const filtered = projects
    .filter((p) => p.name.toLowerCase().includes(searchQuery.toLowerCase()))
    .filter((p) => filterType === 'All' || p.type === filterType);

  return (
    <div className="flex-1 bg-[#F8FAFC] text-slate-900 overflow-y-auto p-6 lg:p-10 font-sans select-none space-y-6 lg:space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl lg:text-3xl font-black tracking-tight text-slate-900">All Projects</h1>
          <p className="text-xs text-slate-500 font-medium">Every model and drawing in your workspace.</p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="relative flex items-center flex-1 sm:flex-initial">
            <Search className="w-4 h-4 text-slate-400 absolute left-3" />
            <input
              type="text"
              placeholder="Search projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 outline-none w-full sm:w-64 shadow-xs focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
            />
          </div>

          <button
            onClick={() => setNewProjectModalOpen(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-600/20 flex items-center space-x-1.5 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New Project</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs & Refresh */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-1 bg-white border border-slate-200 p-1 rounded-xl">
          {(['All', '3D', '2D'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                filterType === t ? 'bg-indigo-600 text-white shadow-xs' : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              {t} Projects
            </button>
          ))}
        </div>

        <button
          onClick={fetchProjects}
          className="p-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-xl text-xs font-semibold flex items-center space-x-1 transition-all"
          title="Refresh Projects"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Projects Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 lg:gap-5">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-44 bg-slate-200/60 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="p-16 text-center bg-white border border-slate-200/90 rounded-2xl space-y-3">
          <Hexagon className="w-10 h-10 text-slate-300 mx-auto" />
          <h3 className="text-sm font-bold text-slate-700">No projects found</h3>
          <p className="text-xs text-slate-400">
            {searchQuery ? 'No matching projects for your query.' : 'Create a new project to get started.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 lg:gap-5">
          {filtered.map((proj) => (
            <ProjectCard
              key={proj.id}
              project={proj}
              onUpdate={(updated) => {
                setProjects((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
              }}
              onDelete={(deletedId) => {
                setProjects((prev) => prev.filter((p) => p.id !== deletedId));
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default ProjectsView;
