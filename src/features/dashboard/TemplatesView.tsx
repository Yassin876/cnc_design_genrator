import React, { useState } from 'react';
import { Search, Circle, Square } from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';

const TemplatesView: React.FC = () => {
  const { loadFile } = useWorkspaceStore();
  const [searchQuery, setSearchQuery] = useState('');

  const templates = [
    { id: 't1', title: 'Flange & Bolt Pattern', tag: 'MECHANICAL', path: 'templates/flange.dxf', is2D: true, iconType: 'circle' },
    { id: 't2', title: 'Pipe Elbow 90°', tag: 'PIPING', path: 'templates/pipe.stl', is2D: false, iconType: 'pipe' },
    { id: 't3', title: 'Enclosure Box', tag: 'HOUSING', path: 'templates/box.stl', is2D: false, iconType: 'square' },
    { id: 't4', title: 'Gear Housing', tag: 'MECHANICAL', path: 'templates/gear.stl', is2D: false, iconType: 'concentric' }
  ];

  const filtered = templates.filter(t => t.title.toLowerCase().includes(searchQuery.toLowerCase()));

  return (
    <div className="flex-1 bg-[#F8FAFC] text-slate-900 overflow-y-auto p-10 font-sans select-none space-y-8">
      
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-black tracking-tight text-slate-900">Templates</h1>
          <p className="text-xs text-slate-500 font-medium">Start faster with a ready-made base model.</p>
        </div>

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
      </div>

      <h2 className="text-sm font-bold text-slate-900">Start from a Template</h2>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        {filtered.map((tpl) => (
          <div
            key={tpl.id}
            onClick={() => loadFile(tpl.path, tpl.is2D ? '2D' : '3D')}
            className="bg-white border border-slate-200/90 hover:border-indigo-300 rounded-2xl overflow-hidden cursor-pointer shadow-xs hover:shadow-md transition-all group"
          >
            {/* Preview Box */}
            <div className="h-32 bg-indigo-50/50 flex items-center justify-center border-b border-slate-100 p-4">
              {tpl.iconType === 'circle' && <Circle className="w-10 h-10 text-indigo-400 stroke-1" />}
              {tpl.iconType === 'square' && <Square className="w-10 h-10 text-indigo-400 stroke-1" />}
              {tpl.iconType === 'pipe' && (
                <svg viewBox="0 0 100 100" className="w-12 h-12 stroke-indigo-400 fill-none stroke-[3]" strokeLinecap="round">
                  <path d="M 30 70 L 30 40 Q 30 30 40 30 L 70 30" />
                </svg>
              )}
              {tpl.iconType === 'concentric' && (
                <div className="relative flex items-center justify-center">
                  <Circle className="w-10 h-10 text-indigo-400 stroke-1" />
                  <Circle className="w-5 h-5 text-indigo-400 stroke-1 absolute" />
                </div>
              )}
            </div>

            {/* Meta */}
            <div className="p-4 space-y-1">
              <h4 className="text-xs font-bold text-slate-900 truncate group-hover:text-indigo-600 transition-colors">
                {tpl.title}
              </h4>
              <span className="inline-block text-[9px] font-mono font-bold tracking-wider text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded uppercase">
                {tpl.tag}
              </span>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
};

export default TemplatesView;
