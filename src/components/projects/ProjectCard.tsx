import React, { useState, useRef, useEffect } from 'react';
import { Hexagon, ArrowUpRight, Star, MoreVertical, Trash2, Edit2, Check, X } from 'lucide-react';
import { Project, projectsApiService } from '../../services/api/projects';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';

interface ProjectCardProps {
  project: Project;
  onUpdate?: (updated: Project) => void;
  onDelete?: (projectId: string) => void;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({ project, onUpdate, onDelete }) => {
  const { loadFile } = useWorkspaceStore();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameText, setRenameText] = useState(project.name);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsMenuOpen(false);
      }
    };
    if (isMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isMenuOpen]);

  const handleToggleFavorite = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsMenuOpen(false);
    const newFav = !project.is_favorite;
    if (onUpdate) {
      onUpdate({ ...project, is_favorite: newFav });
    }
    try {
      const res = await projectsApiService.toggleFavorite(project.id);
      if (onUpdate) {
        onUpdate({ ...project, is_favorite: res.is_favorite });
      }
    } catch (err) {
      console.error('Failed to toggle favorite', err);
      if (onUpdate) {
        onUpdate(project);
      }
    }
  };

  const handleMoveToTrash = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsMenuOpen(false);
    if (onDelete) {
      onDelete(project.id);
    }
    try {
      await projectsApiService.moveToTrash(project.id);
    } catch (err) {
      console.error('Failed to move project to trash', err);
    }
  };

  const handleStartRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsMenuOpen(false);
    setRenameText(project.name);
    setIsRenaming(true);
  };

  const handleSaveRename = async (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!renameText.trim()) return;
    const newName = renameText.trim();
    setIsRenaming(false);
    if (onUpdate) {
      onUpdate({ ...project, name: newName });
    }
    try {
      const updated = await projectsApiService.updateProject(project.id, { name: newName });
      if (onUpdate) {
        onUpdate(updated);
      }
    } catch (err) {
      console.error('Failed to rename project', err);
      if (onUpdate) {
        onUpdate(project);
      }
    }
  };

  return (
    <div
      onClick={() => {
        if (!isRenaming) {
          loadFile(project.file_path || project.id, project.type, project.id, project.name);
        }
      }}
      className="bg-white border border-slate-200/90 hover:border-indigo-300 rounded-2xl overflow-hidden cursor-pointer shadow-xs hover:shadow-md transition-all group relative flex flex-col justify-between"
    >
      {/* Thumbnail Area */}
      <div className="h-32 bg-indigo-50/50 flex items-center justify-center border-b border-slate-100 p-4 relative">
        {project.type === '3D' ? (
          <Hexagon className="w-10 h-10 text-indigo-400 stroke-1 group-hover:scale-105 transition-transform" />
        ) : (
          <ArrowUpRight className="w-10 h-10 text-indigo-400 stroke-1 group-hover:scale-105 transition-transform" />
        )}

        {/* Top-Right Actions: Star + 3-dots Menu */}
        <div className="absolute top-3 right-3 flex items-center space-x-1">
          {/* Star Favorite Button */}
          <button
            onClick={handleToggleFavorite}
            className={`p-1.5 rounded-lg border transition-all ${
              project.is_favorite
                ? 'bg-amber-500 border-amber-500 text-white shadow-xs'
                : 'bg-white/90 hover:bg-white border-slate-200 text-slate-400 hover:text-amber-500'
            }`}
            title={project.is_favorite ? 'Remove Favorite' : 'Mark as Favorite'}
          >
            <Star className={`w-3.5 h-3.5 ${project.is_favorite ? 'fill-current' : ''}`} />
          </button>

          {/* 3-Dots Menu Button */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsMenuOpen((prev) => !prev);
              }}
              className={`p-1.5 rounded-lg border transition-all ${
                isMenuOpen
                  ? 'bg-slate-900 text-white border-slate-900 shadow-xs'
                  : 'bg-white/90 hover:bg-white border-slate-200 text-slate-500 hover:text-slate-800'
              }`}
              title="Project Actions"
            >
              <MoreVertical className="w-3.5 h-3.5" />
            </button>

            {/* Dropdown Menu */}
            {isMenuOpen && (
              <div
                onClick={(e) => e.stopPropagation()}
                className="absolute right-0 mt-1.5 w-44 bg-white border border-slate-200 rounded-xl shadow-xl py-1 z-30 animate-in fade-in zoom-in-95 duration-100 font-sans"
              >
                <button
                  onClick={handleToggleFavorite}
                  className="w-full px-3 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center space-x-2 transition-colors"
                >
                  <Star className={`w-3.5 h-3.5 ml-1 ${project.is_favorite ? 'text-amber-500 fill-amber-500' : 'text-slate-400'}`} />
                  <span>{project.is_favorite ? 'Remove from Favorites' : 'Add to Favorites'}</span>
                </button>

                <button
                  onClick={handleStartRename}
                  className="w-full px-3 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center space-x-2 transition-colors"
                >
                  <Edit2 className="w-3.5 h-3.5 ml-1 text-slate-400" />
                  <span>Rename</span>
                </button>

                <div className="my-1 border-t border-slate-100" />

                <button
                  onClick={handleMoveToTrash}
                  className="w-full px-3 py-2 text-left text-xs font-medium text-rose-600 hover:bg-rose-50 flex items-center space-x-2 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5 ml-1 text-rose-500" />
                  <span>Delete</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Card Info / Rename Input */}
      <div className="p-4 space-y-2">
        {isRenaming ? (
          <form onSubmit={handleSaveRename} className="flex items-center space-x-1" onClick={(e) => e.stopPropagation()}>
            <input
              type="text"
              autoFocus
              value={renameText}
              onChange={(e) => setRenameText(e.target.value)}
              className="px-2 py-1 border border-indigo-500 rounded-lg text-xs font-bold text-slate-900 w-full outline-none"
            />
            <button
              type="submit"
              className="p-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded-md"
              title="Save"
            >
              <Check className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setIsRenaming(false)}
              className="p-1 text-slate-400 hover:text-slate-600 rounded-md"
              title="Cancel"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </form>
        ) : (
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-900 truncate group-hover:text-indigo-600 transition-colors">
              {project.name}
            </h4>
          </div>
        )}

        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span className="font-semibold text-indigo-600/80">{project.type} Project</span>
          <span>v{project.current_version || 1}</span>
        </div>
      </div>
    </div>
  );
};
