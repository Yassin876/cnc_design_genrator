import React, { useState, useEffect } from 'react';
import { 
  Search, Hexagon, ArrowUpRight, Layers, Download, 
  Grid, List, Circle, RefreshCw, Star
} from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { useAuthStore } from '../../app/store/useAuthStore';
import { projectsApiService, Project } from '../../services/api/projects';
import { ProjectCard } from '../../components/projects/ProjectCard';

const HomeView: React.FC = () => {
  const { setViewMode, loadFile, setNewProjectModalOpen, setImportModalOpen } = useWorkspaceStore();
  const { user } = useAuthStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [viewLayout, setViewLayout] = useState<'grid' | 'list'>('grid');
  const [recentProjects, setRecentProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const userName = user?.name ? user.name.split(' ')[0] : 'Engineer';

  const fetchRecent = async () => {
    setIsLoading(true);
    try {
      const data = await projectsApiService.getRecentProjects(8);
      setRecentProjects(data);
    } catch (err) {
      console.error('Failed to fetch recent projects for HomeView', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRecent();
  }, []);

  const handleToggleFavorite = async (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation();
    // Optimistic UI update
    setRecentProjects((prev) =>
      prev.map((p) => (p.id === projectId ? { ...p, is_favorite: !p.is_favorite } : p))
    );
    try {
      const res = await projectsApiService.toggleFavorite(projectId);
      setRecentProjects((prev) =>
        prev.map((p) => (p.id === projectId ? { ...p, is_favorite: res.is_favorite } : p))
      );
    } catch (err) {
      console.error('Failed to toggle favorite', err);
      fetchRecent();
    }
  };

  const filtered = recentProjects.filter((p) => 
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex-1 bg-[#F8FAFC] text-slate-900 overflow-y-auto p-6 lg:p-10 font-sans select-none space-y-8 lg:space-y-10">
      
      {/* Top Header & Search */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl lg:text-3xl font-black tracking-tight text-slate-900">
            Welcome, {userName}.
          </h1>
          <p className="text-xs text-slate-500 font-medium">
            What would you like to design today?
          </p>
        </div>

        <div className="relative flex items-center">
          <Search className="w-4 h-4 text-slate-400 absolute left-3" />
          <input
            type="text"
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 outline-none w-full sm:w-64 shadow-xs focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
          />
        </div>
      </div>

      {/* 4 Quick Action Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-5">
        
        {/* Create 3D Model */}
        <div
          onClick={() => setViewMode('workspace_3d')}
          className="bg-white border border-slate-200/90 hover:border-indigo-300 p-6 rounded-2xl cursor-pointer shadow-xs hover:shadow-md transition-all space-y-3 group"
        >
          <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600 group-hover:scale-105 transition-transform">
            <Hexagon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-900">Create 3D Model</h3>
            <p className="text-[11px] text-slate-400 mt-0.5 font-medium">Parametric 3D Workspace</p>
          </div>
        </div>

        {/* Create 2D Drawing */}
        <div
          onClick={() => setViewMode('workspace_2d')}
          className="bg-white border border-slate-200/90 hover:border-indigo-300 p-6 rounded-2xl cursor-pointer shadow-xs hover:shadow-md transition-all space-y-3 group"
        >
          <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600 group-hover:scale-105 transition-transform">
            <ArrowUpRight className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-900">Create 2D Drawing</h3>
            <p className="text-[11px] text-slate-400 mt-0.5 font-medium">DXF Blueprint & AI Generation</p>
          </div>
        </div>

        {/* Open Existing Project */}
        <div
          onClick={() => setViewMode('projects')}
          className="bg-white border border-slate-200/90 hover:border-indigo-300 p-6 rounded-2xl cursor-pointer shadow-xs hover:shadow-md transition-all space-y-3 group"
        >
          <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600 group-hover:scale-105 transition-transform">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-900">Open Existing Project</h3>
            <p className="text-[11px] text-slate-400 mt-0.5 font-medium">Browse All User Projects</p>
          </div>
        </div>

        {/* Import CAD File */}
        <div
          onClick={() => setImportModalOpen(true)}
          className="bg-white border border-slate-200/90 hover:border-indigo-300 p-6 rounded-2xl cursor-pointer shadow-xs hover:shadow-md transition-all space-y-3 group"
        >
          <div className="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center text-amber-600 group-hover:scale-105 transition-transform">
            <Download className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-900">Import CAD File</h3>
            <p className="text-[11px] text-slate-400 mt-0.5 font-medium">STL, STEP, OBJ, DXF</p>
          </div>
        </div>

      </div>

      {/* Recent Projects Section */}
      <div className="space-y-4">
        
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-900">Recent Projects</h2>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={fetchRecent}
              className="p-1 text-slate-400 hover:text-slate-600 rounded"
              title="Refresh"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            <div className="flex items-center space-x-1 bg-white border border-slate-200 p-1 rounded-lg">
              <button
                onClick={() => setViewLayout('grid')}
                className={`p-1 rounded ${viewLayout === 'grid' ? 'bg-slate-100 text-slate-900' : 'text-slate-400'}`}
              >
                <Grid className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setViewLayout('list')}
                className={`p-1 rounded ${viewLayout === 'list' ? 'bg-slate-100 text-slate-900' : 'text-slate-400'}`}
              >
                <List className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Project Grid / Empty State */}
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 lg:gap-5">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-44 bg-slate-200/60 rounded-2xl animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center bg-white border border-slate-200/90 rounded-2xl space-y-3">
            <Hexagon className="w-10 h-10 text-slate-300 mx-auto" />
            <h3 className="text-sm font-bold text-slate-700">No recent projects yet</h3>
            <p className="text-xs text-slate-400">Create a 3D model or 2D drawing to start designing.</p>
            <button
              onClick={() => setNewProjectModalOpen(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs rounded-xl shadow-sm transition-all inline-block"
            >
              Create First Project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 lg:gap-5">
            {filtered.map((proj) => (
              <ProjectCard
                key={proj.id}
                project={proj}
                onUpdate={(updated) => {
                  setRecentProjects((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
                }}
                onDelete={(deletedId) => {
                  setRecentProjects((prev) => prev.filter((p) => p.id !== deletedId));
                }}
              />
            ))}
          </div>
        )}

      </div>

    </div>
  );
};

export default HomeView;
