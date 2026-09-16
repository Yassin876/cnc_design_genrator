import React from 'react';
import { 
  Home, Folder, Clock, Hexagon, ArrowUpRight, 
  BookOpen, Star, Trash2, Settings
} from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { useAuthStore } from '../../app/store/useAuthStore';
import { ViewMode } from '../../types';
import { BrandLogo } from '../common/BrandLogo';

export const AppSidebar: React.FC = () => {
  const { viewMode, setViewMode } = useWorkspaceStore();
  const { user } = useAuthStore();

  const userName = user?.name || 'Engineer';

  const isCurrent = (mode: ViewMode) => viewMode === mode || (mode === 'home' && viewMode === 'dashboard');

  return (
    <aside className="w-60 bg-white border-r border-slate-200/90 flex flex-col justify-between p-4 select-none font-sans text-xs shrink-0 z-40">
      
      <div className="space-y-6">
        
        {/* Logo */}
        <div 
          onClick={() => setViewMode('home')}
          className="flex items-center space-x-2.5 px-2 py-1 cursor-pointer group"
        >
          <BrandLogo size="md" />
        </div>

        {/* Top Navigation */}
        <div className="space-y-1">
          <button
            onClick={() => setViewMode('home')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-xl text-right font-medium transition-all ${
              isCurrent('home') 
                ? 'bg-indigo-50 text-indigo-600 font-bold' 
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <Home className="w-4 h-4 ml-2" />
            <span>Home</span>
          </button>

          <button
            onClick={() => setViewMode('projects')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-xl text-right font-medium transition-all ${
              isCurrent('projects') 
                ? 'bg-indigo-50 text-indigo-600 font-bold' 
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <Folder className="w-4 h-4 ml-2" />
            <span>Projects</span>
          </button>

          <button
            onClick={() => setViewMode('recent')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-xl text-right font-medium transition-all ${
              isCurrent('recent') 
                ? 'bg-indigo-50 text-indigo-600 font-bold' 
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <Clock className="w-4 h-4 ml-2" />
            <span>Recent</span>
          </button>
        </div>

        {/* WORKSPACES section */}
        <div className="space-y-1 pt-2">
          <div className="px-3 text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
            Workspaces
          </div>

          <button
            onClick={() => setViewMode('workspace_3d')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-xl text-right font-medium transition-all ${
              isCurrent('workspace_3d') 
                ? 'bg-indigo-50 text-indigo-600 font-bold' 
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <Hexagon className="w-4 h-4 ml-2" />
            <span>3D CAD Workspace</span>
          </button>

          <button
            onClick={() => setViewMode('workspace_2d')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-xl text-right font-medium transition-all ${
              isCurrent('workspace_2d') 
                ? 'bg-indigo-50 text-indigo-600 font-bold' 
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <ArrowUpRight className="w-4 h-4 ml-2" />
            <span>2D DXF Workspace</span>
          </button>
        </div>

        {/* LIBRARY section */}
        <div className="space-y-1 pt-2">
          <div className="px-3 text-[10px] font-mono font-bold uppercase tracking-wider text-slate-400">
            Library
          </div>

          <button
            onClick={() => setViewMode('templates')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-xl text-right font-medium transition-all ${
              isCurrent('templates') 
                ? 'bg-indigo-50 text-indigo-600 font-bold' 
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <BookOpen className="w-4 h-4 ml-2" />
            <span>Templates</span>
          </button>

          <button
            onClick={() => setViewMode('favorites')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-xl text-right font-medium transition-all ${
              isCurrent('favorites') 
                ? 'bg-indigo-50 text-indigo-600 font-bold' 
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <Star className="w-4 h-4 ml-2" />
            <span>Favorites</span>
          </button>

          <button
            onClick={() => setViewMode('trash')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-xl text-right font-medium transition-all ${
              isCurrent('trash') 
                ? 'bg-indigo-50 text-indigo-600 font-bold' 
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <Trash2 className="w-4 h-4 ml-2" />
            <span>Trash</span>
          </button>
        </div>

      </div>

      {/* Bottom Section */}
      <div className="space-y-3 border-t border-slate-100 pt-3">
        <button
          onClick={() => setViewMode('settings')}
          className={`w-full flex items-center space-x-3 px-3 py-2 rounded-xl text-right font-medium transition-all ${
            isCurrent('settings') 
              ? 'bg-indigo-50 text-indigo-600 font-bold' 
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`}
        >
          <Settings className="w-4 h-4 ml-2" />
          <span>Settings</span>
        </button>

        {/* User Profile Pill */}
        <div className="flex items-center space-x-3 p-2 rounded-xl bg-slate-50 border border-slate-100 mt-2">
          {user?.avatar_url ? (
            <div className="w-8 h-8 rounded-full overflow-hidden border border-indigo-200 ml-2 shrink-0 bg-white">
              <img src={user.avatar_url} alt={userName} className="w-full h-full object-contain" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-full bg-indigo-600 text-white font-bold flex items-center justify-center text-xs shadow-sm ml-2 shrink-0">
              {userName.charAt(0).toUpperCase()}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <div className="text-xs font-bold text-slate-900 truncate">{userName}</div>
            <div className="text-[10px] text-slate-400 font-medium">Pro Account</div>
          </div>
        </div>
      </div>

    </aside>
  );
};
