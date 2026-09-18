import React, { useState, useEffect } from 'react';
import { Search, Hexagon, ArrowUpRight, Clock, Star, RefreshCw } from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { projectsApiService, Project } from '../../services/api/projects';

const RecentView: React.FC = () => {
  const { loadFile } = useWorkspaceStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [recentProjects, setRecentProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchRecent = async () => {
    setIsLoading(true);
    try {
      const data = await projectsApiService.getRecentProjects(12);
      setRecentProjects(data);
    } catch (err) {
      console.error('Failed to fetch recent projects', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRecent();
  }, []);

  const filtered = recentProjects.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex-1 bg-[#F8FAFC] text-slate-900 overflow-y-auto p-10 font-sans select-none space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-black tracking-tight text-slate-900">Recently Opened</h1>
          <p className="text-xs text-slate-500 font-medium">Pick up right where you left off.</p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="relative flex items-center">
            <Search className="w-4 h-4 text-slate-400 absolute left-3" />
            <input
              type="text"
              placeholder="Search projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 outline-none w-64 shadow-xs focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
            />
          </div>

          <button
            onClick={fetchRecent}
            className="p-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-xl text-xs font-semibold"
            title="Refresh Recent"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <h2 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
        <Clock className="w-4 h-4 text-indigo-600" />
        <span>Recent Work</span>
      </h2>

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-44 bg-slate-200/60 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="p-16 text-center bg-white border border-slate-200/90 rounded-2xl space-y-2">
          <Clock className="w-10 h-10 text-slate-300 mx-auto" />
          <h3 className="text-sm font-bold text-slate-700">No recently modified projects</h3>
          <p className="text-xs text-slate-400">Open or edit a project to see it appear here.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
          {filtered.map((proj) => (
            <div
              key={proj.id}
              onClick={() => loadFile(proj.file_path || proj.id, proj.type, proj.id, proj.name)}
              className="bg-white border border-slate-200/90 hover:border-indigo-300 rounded-2xl overflow-hidden cursor-pointer shadow-xs hover:shadow-md transition-all group relative"
            >
              <div className="h-32 bg-indigo-50/50 flex items-center justify-center border-b border-slate-100 p-4">
                {proj.type === '3D' ? (
                  <Hexagon className="w-10 h-10 text-indigo-400 stroke-1" />
                ) : (
                  <ArrowUpRight className="w-10 h-10 text-indigo-400 stroke-1" />
                )}
              </div>

              <div className="p-4 space-y-1">
                <h4 className="text-xs font-bold text-slate-900 truncate group-hover:text-indigo-600 transition-colors">
                  {proj.name}
                </h4>
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span className="font-semibold text-indigo-600/80">{proj.type} Project</span>
                  <span>v{proj.current_version}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default RecentView;
