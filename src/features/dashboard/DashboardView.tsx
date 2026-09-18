import React, { useState } from 'react';
import { 
  Plus, Search, Grid, List, Folder, FileCode, Clock, ShieldCheck, Download, 
  Sparkles, Wrench, ArrowRight, Layers, Trash2, Edit3, MoreVertical, Box, User, LogOut, Lock
} from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { useAuthStore } from '../../app/store/useAuthStore';

export const DashboardView: React.FC = () => {
  const { setViewMode, loadFile, setNewProjectModalOpen, setImportModalOpen, setAuthModalOpen } = useWorkspaceStore();
  const { user, logout } = useAuthStore();

  const [viewLayout, setViewLayout] = useState<'grid' | 'list'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<'All' | '3D' | '2D'>('All');

  const templates = [
    { title: 'Industrial Pipe Elbow', type: '3D CAD', desc: '90° elbow pipe with mounting flanges and inner flow diameter.', path: 'templates/pipe_elbow.stl', is2D: false },
    { title: 'Motor Mount Adapter Plate', type: '2D DXF', desc: 'CNC milled aluminum plate with NEMA23 bolt pattern.', path: 'templates/motor_mount.dxf', is2D: true },
    { title: 'Spindle Bearing Housing', type: '3D CAD', desc: 'Precision CNC lathe turned cylindrical bearing block.', path: 'templates/bearing_block.stl', is2D: false },
    { title: 'Nesting Sheet Assembly', type: '2D Layout', desc: 'Optimized 4x8ft sheet metal cut layout with micro-tabs.', path: 'templates/nesting_sheet.dxf', is2D: true }
  ];

  const recentProjects = [
    { id: 'p1', name: 'Industrial Pipe Elbow 90-Deg', type: '3D CAD', status: 'Machining Ready', version: 3, updated: '10 mins ago', path: 'storage/uploads/elbow.stl', is2D: false },
    { id: 'p2', name: 'Flange Plate Bracket', type: '2D DXF', status: 'Validating', version: 1, updated: '2 hours ago', path: 'storage/uploads/bracket.dxf', is2D: true },
    { id: 'p3', name: 'Enclosure Top Cover', type: '3D CAD', status: 'Draft', version: 2, updated: '1 day ago', path: 'storage/uploads/cover.stl', is2D: false }
  ];

  const filteredProjects = recentProjects
    .filter(p => p.name.toLowerCase().includes(searchQuery.toLowerCase()))
    .filter(p => filterType === 'All' || p.type.includes(filterType));

  return (
    <div className="flex-1 bg-cad-bg overflow-y-auto p-8 select-none font-sans space-y-8">
      
      {/* Top Banner & User Profile */}
      <div className="flex items-center justify-between border-b border-cad-border pb-6">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <h1 className="text-2xl font-bold text-white tracking-tight">Engineering Control Hub</h1>
            <span className="text-xs font-mono bg-violet-950 text-violet-300 border border-violet-800 px-2.5 py-0.5 rounded-full font-bold">
              v2.5 Production Suite
            </span>
          </div>
          <p className="text-xs text-cad-textMuted font-mono">
            Parametric 3D CAD / 2D DXF Blueprinting & DFM Machining Suite
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {user ? (
            <div className="flex items-center space-x-3 bg-cad-panel border border-cad-border px-3 py-1.5 rounded-xl">
              <div className="w-7 h-7 rounded-full bg-violet-600 flex items-center justify-center text-xs font-bold text-white">
                {user.name.charAt(0).toUpperCase()}
              </div>
              <div className="text-xs">
                <span className="text-white font-bold block">{user.name}</span>
                <span className="text-[10px] text-cad-textMuted font-mono">{user.email}</span>
              </div>
              <button
                onClick={() => logout()}
                className="text-cad-textMuted hover:text-red-400 p-1 rounded-lg hover:bg-cad-surface ml-2"
                title="Sign Out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setViewMode('auth')}
              className="bg-cad-panel hover:bg-cad-surface border border-cad-border text-white text-xs font-bold px-4 py-2 rounded-xl flex items-center space-x-1.5"
            >
              <Lock className="w-3.5 h-3.5 text-violet-400" />
              <span>Sign In</span>
            </button>
          )}

          <button
            onClick={() => setNewProjectModalOpen(true)}
            className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-bold text-xs px-4 py-2.5 rounded-xl shadow-lg shadow-violet-600/30 flex items-center space-x-2 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New CNC Project</span>
          </button>
        </div>
      </div>

      {/* Quick Launch Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div
          onClick={() => setNewProjectModalOpen(true)}
          className="group bg-cad-panel hover:bg-cad-surface border border-cad-border hover:border-violet-500 p-5 rounded-2xl cursor-pointer transition-all space-y-2"
        >
          <Sparkles className="w-8 h-8 text-violet-400 group-hover:scale-110 transition-transform" />
          <h3 className="text-sm font-bold text-white">AI CAD Generator</h3>
          <p className="text-xs text-cad-textMuted leading-relaxed">
            Generate parametric 3D models or 2D DXF blueprints from text prompts.
          </p>
        </div>

        <div
          onClick={() => setImportModalOpen(true)}
          className="group bg-cad-panel hover:bg-cad-surface border border-cad-border hover:border-cyan-500 p-5 rounded-2xl cursor-pointer transition-all space-y-2"
        >
          <Folder className="w-8 h-8 text-cyan-400 group-hover:scale-110 transition-transform" />
          <h3 className="text-sm font-bold text-white">Import CAD File</h3>
          <p className="text-xs text-cad-textMuted leading-relaxed">
            Open STL, STEP, OBJ, or DXF files with instant geometry inspection.
          </p>
        </div>

        <div
          onClick={() => setViewMode('workspace_2d')}
          className="group bg-cad-panel hover:bg-cad-surface border border-cad-border hover:border-amber-500 p-5 rounded-2xl cursor-pointer transition-all space-y-2"
        >
          <FileCode className="w-8 h-8 text-amber-400 group-hover:scale-110 transition-transform" />
          <h3 className="text-sm font-bold text-white">2D CAD Blueprinting</h3>
          <p className="text-xs text-cad-textMuted leading-relaxed">
            Vector CAD canvas with layer management, dimensions, and snap tools.
          </p>
        </div>

        <div
          onClick={() => setViewMode('nesting')}
          className="group bg-cad-panel hover:bg-cad-surface border border-cad-border hover:border-emerald-500 p-5 rounded-2xl cursor-pointer transition-all space-y-2"
        >
          <Layers className="w-8 h-8 text-emerald-400 group-hover:scale-110 transition-transform" />
          <h3 className="text-sm font-bold text-white">CAM Sheet Nesting</h3>
          <p className="text-xs text-cad-textMuted leading-relaxed">
            Optimize 2D part layouts on raw sheet metal stock to minimize waste.
          </p>
        </div>
      </div>

      {/* Templates & Presets */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
            Engineering Templates & Presets
          </h2>
        </div>

        <div className="grid grid-cols-4 gap-4">
          {templates.map((tpl, i) => (
            <div
              key={i}
              onClick={() => loadFile(tpl.path, tpl.is2D ? '2D' : '3D')}
              className="group bg-cad-panel hover:bg-cad-surface border border-cad-border hover:border-violet-500/60 p-4 rounded-xl cursor-pointer transition-all space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white group-hover:text-violet-300 transition-colors">
                  {tpl.title}
                </span>
                <span className="text-[10px] font-mono bg-cad-bg border border-cad-border text-cad-textMuted px-1.5 py-0.5 rounded">
                  {tpl.type}
                </span>
              </div>
              <p className="text-[11px] text-cad-textMuted line-clamp-2 leading-relaxed">
                {tpl.desc}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Projects Table / Grid */}
      <div className="space-y-4 pt-2">
        
        {/* Controls Bar */}
        <div className="flex items-center justify-between bg-cad-panel border border-cad-border p-3 rounded-xl">
          <div className="flex items-center space-x-3">
            <div className="flex items-center bg-cad-bg border border-cad-border rounded-lg px-3 py-1.5 text-xs w-64">
              <Search className="w-4 h-4 text-cad-textMuted mr-2" />
              <input
                type="text"
                placeholder="Search projects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-transparent text-white outline-none w-full"
              />
            </div>

            <div className="flex items-center space-x-1 bg-cad-bg p-0.5 rounded-lg border border-cad-border text-xs font-mono">
              {['All', '3D', '2D'].map((t) => (
                <button
                  key={t}
                  onClick={() => setFilterType(t as any)}
                  className={`px-2.5 py-1 rounded font-bold transition-all ${
                    filterType === t ? 'bg-violet-600 text-white' : 'text-cad-textMuted hover:text-white'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <div className="flex bg-cad-bg p-0.5 rounded-lg border border-cad-border">
              <button
                onClick={() => setViewLayout('grid')}
                className={`p-1.5 rounded ${viewLayout === 'grid' ? 'bg-cad-surface text-white' : 'text-cad-textMuted'}`}
              >
                <Grid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewLayout('list')}
                className={`p-1.5 rounded ${viewLayout === 'list' ? 'bg-cad-surface text-white' : 'text-cad-textMuted'}`}
              >
                <List className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Project Cards Grid */}
        {viewLayout === 'grid' ? (
          <div className="grid grid-cols-3 gap-4">
            {filteredProjects.map((proj) => (
              <div
                key={proj.id}
                onClick={() => loadFile(proj.path, proj.is2D ? '2D' : '3D')}
                className="group bg-cad-panel hover:bg-cad-surface border border-cad-border hover:border-violet-500/60 p-5 rounded-2xl cursor-pointer transition-all space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Box className="w-4 h-4 text-violet-400" />
                    <h4 className="text-sm font-bold text-white group-hover:text-violet-300 transition-colors">
                      {proj.name}
                    </h4>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                    proj.status === 'Machining Ready' 
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' 
                      : 'bg-amber-950 text-amber-300 border border-amber-800'
                  }`}>
                    {proj.status}
                  </span>
                </div>

                <div className="flex items-center justify-between text-xs font-mono text-cad-textMuted border-t border-cad-border pt-3">
                  <span>Version v{proj.version}</span>
                  <span>{proj.updated}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-cad-panel border border-cad-border rounded-2xl overflow-hidden font-mono text-xs">
            {filteredProjects.map((proj) => (
              <div
                key={proj.id}
                onClick={() => loadFile(proj.path, proj.is2D ? '2D' : '3D')}
                className="flex items-center justify-between p-4 border-b border-cad-border hover:bg-cad-surface cursor-pointer transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <Box className="w-4 h-4 text-violet-400" />
                  <span className="font-bold text-white">{proj.name}</span>
                </div>

                <div className="flex items-center space-x-6">
                  <span className="text-cad-textMuted">{proj.type}</span>
                  <span className="text-cad-textMuted">v{proj.version}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    proj.status === 'Machining Ready' 
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800' 
                      : 'bg-amber-950 text-amber-300 border border-amber-800'
                  }`}>
                    {proj.status}
                  </span>
                  <span className="text-cad-textMuted">{proj.updated}</span>
                </div>
              </div>
            ))}
          </div>
        )}

      </div>

    </div>
  );
};
