import React, { useState, useEffect } from 'react';
import { Search, Star, Hexagon, ArrowUpRight, RefreshCw } from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { projectsApiService, Project } from '../../services/api/projects';
import { ProjectCard } from '../../components/projects/ProjectCard';

const FavoritesView: React.FC = () => {
  const { loadFile } = useWorkspaceStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [favorites, setFavorites] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchFavorites = async () => {
    setIsLoading(true);
    try {
      const data = await projectsApiService.getFavoriteProjects();
      setFavorites(data);
    } catch (err) {
      console.error('Failed to fetch favorites', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFavorites();
  }, []);

  const handleRemoveFavorite = async (e: React.MouseEvent, projectId: string) => {
    e.stopPropagation();
    try {
      await projectsApiService.toggleFavorite(projectId);
      setFavorites((prev) => prev.filter((p) => p.id !== projectId));
    } catch (err) {
      console.error('Failed to remove from favorites', err);
    }
  };

  const filtered = favorites.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex-1 bg-[#F8FAFC] text-slate-900 overflow-y-auto p-10 font-sans select-none space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-black tracking-tight text-slate-900">Favorites</h1>
          <p className="text-xs text-slate-500 font-medium">Your starred projects, always close at hand.</p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="relative flex items-center">
            <Search className="w-4 h-4 text-slate-400 absolute left-3" />
            <input
              type="text"
              placeholder="Search favorites..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 outline-none w-64 focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
            />
          </div>

          <button
            onClick={fetchFavorites}
            className="p-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-xl"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <h2 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
        <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
        <span>Starred Projects</span>
      </h2>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-44 bg-slate-200/60 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="p-16 text-center bg-white border border-slate-200/90 rounded-2xl space-y-2">
          <Star className="w-10 h-10 text-slate-300 mx-auto" />
          <h3 className="text-sm font-bold text-slate-700">No favorites yet</h3>
          <p className="text-xs text-slate-400">
            Click the ⭐ on any project card to add it here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 lg:gap-5">
          {filtered.map((proj) => (
            <ProjectCard
              key={proj.id}
              project={proj}
              onUpdate={(updated) => {
                if (!updated.is_favorite) {
                  setFavorites((prev) => prev.filter((p) => p.id !== updated.id));
                } else {
                  setFavorites((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
                }
              }}
              onDelete={(deletedId) => {
                setFavorites((prev) => prev.filter((p) => p.id !== deletedId));
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default FavoritesView;
