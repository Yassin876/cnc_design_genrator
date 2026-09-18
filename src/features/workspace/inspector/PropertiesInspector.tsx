import React, { useState, useEffect } from 'react';
import {
  ChevronDown, Layers, Eye, EyeOff, Trash2,
  Box, FileCode, Plus, Edit2, Check, X
} from 'lucide-react';
import { useWorkspaceStore } from '../../../app/store/useWorkspaceStore';
import { use2DWorkspaceStore } from '../../../app/store/use2DWorkspaceStore';
import { use3DWorkspaceStore, Part3D } from '../../../app/store/use3DWorkspaceStore';
import { TreeNode } from '../../../types';

// ── 2D Inspector ─────────────────────────────────────────────────────────────
const Inspector2D: React.FC = () => {
  const { width, height, toolDiameter, setWidth, setHeight, setToolDiameter, inputErrors, validateInputs } = use2DWorkspaceStore();
  const [totalPerimeter, setTotalPerimeter] = useState((width + height) * 2);

  // Recalculate total perimeter when dimensions change
  React.useEffect(() => {
    setTotalPerimeter((width + height) * 2);
  }, [width, height]);

  // Handle input changes with validation
  const handleWidthChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(e.target.value);
    setWidth(value || 0);
    validateInputs();
  };

  const handleHeightChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(e.target.value);
    setHeight(value || 0);
    validateInputs();
  };

  const handleToolDiameterChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(e.target.value);
    setToolDiameter(value || 0);
    validateInputs();
  };

  return (
    <div className="p-4 space-y-6 flex-1">

      {/* 2D BLUEPRINT DIMENSIONS */}
      <div className="space-y-3">
        <div className="flex items-center justify-between text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
          <span>2D Dimensions</span>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
        </div>

        <div className="space-y-2">
          {/* Width (X) */}
          <div className={`flex items-center justify-between border rounded-xl px-3 py-2 ${inputErrors.width ? 'bg-rose-50 border-rose-300' : 'bg-slate-50 border-slate-200'}`}>
            <span className="font-sans text-slate-600 font-bold text-xs">Width (X) <span className="text-rose-500">*</span></span>
            <div className="flex items-center space-x-1 font-mono font-semibold text-slate-900">
              <input
                type="number"
                min="0.1"
                step="1"
                value={width}
                onChange={handleWidthChange}
                data-testid="width-input"
                className="bg-transparent text-right outline-none w-20 text-slate-900 font-bold text-xs"
              />
              <span className="text-[10px] text-slate-400">mm</span>
            </div>
          </div>
          {inputErrors.width && <p className="text-[10px] text-rose-600 px-1">{inputErrors.width}</p>}

          {/* Height (Y) */}
          <div className={`flex items-center justify-between border rounded-xl px-3 py-2 ${inputErrors.height ? 'bg-rose-50 border-rose-300' : 'bg-slate-50 border-slate-200'}`}>
            <span className="font-sans text-slate-600 font-bold text-xs">Height (Y) <span className="text-rose-500">*</span></span>
            <div className="flex items-center space-x-1 font-mono font-semibold text-slate-900">
              <input
                type="number"
                min="0.1"
                step="1"
                value={height}
                onChange={handleHeightChange}
                data-testid="height-input"
                className="bg-transparent text-right outline-none w-20 text-slate-900 font-bold text-xs"
              />
              <span className="text-[10px] text-slate-400">mm</span>
            </div>
          </div>
          {inputErrors.height && <p className="text-[10px] text-rose-600 px-1">{inputErrors.height}</p>}

          {/* Tool Diameter */}
          <div className={`flex items-center justify-between border rounded-xl px-3 py-2 ${inputErrors.toolDiameter ? 'bg-rose-50 border-rose-300' : 'bg-slate-50 border-slate-200'}`}>
            <span className="font-sans text-slate-600 font-bold text-xs">Tool Diameter</span>
            <div className="flex items-center space-x-1 font-mono font-semibold text-slate-900">
              <input
                type="number"
                min="0.5"
                step="0.5"
                value={toolDiameter}
                onChange={handleToolDiameterChange}
                data-testid="tool-diameter-input"
                className="bg-transparent text-right outline-none w-16 text-slate-900 font-bold text-xs"
              />
              <span className="text-[10px] text-slate-400">mm</span>
            </div>
          </div>
          {inputErrors.toolDiameter && <p className="text-[10px] text-rose-600 px-1">{inputErrors.toolDiameter}</p>}
        </div>
      </div>

      {/* Reactive Total Perimeter Card */}
      <div className="space-y-3 pt-2">
        <div className="flex items-center justify-between text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
          <span>Boundary Summary</span>
        </div>
        <div className="bg-emerald-50/60 border border-emerald-200 rounded-xl p-3">
          <div className="flex items-center justify-between">
            <span className="font-sans text-emerald-900 font-bold text-xs">Total Perimeter</span>
            <div className="flex items-center space-x-1 font-mono font-bold text-emerald-700 text-xs">
              <span data-testid="total-perimeter-value" id="total-perimeter">{totalPerimeter.toFixed(1)}</span>
              <span data-testid="total-perimeter" className="hidden">{totalPerimeter.toFixed(1)}</span>
              <span className="text-[10px] text-emerald-600">mm</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ── 3D Inspector ─────────────────────────────────────────────────────────────
const Inspector3D: React.FC = () => {
  const {
    length, width, height, setLength, setWidth, setHeight,
    parts, treeNodes, selectedNodeId, selectNode, togglePartVisibility, removePart,
    renamePart, addNewPart, updatePartDimensions, updatePartPosition,
    assemblyMode, toggleAssemblyMode, inputErrors
  } = use3DWorkspaceStore();

  const [inspectorTab, setInspectorTab] = useState<'inspector' | 'tree'>('inspector');
  const [editingPartId, setEditingPartId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState<string>('');

  const selectedPart = parts.find(p => p.id === selectedNodeId) || parts[0];

  const handleStartRename = (part: Part3D) => {
    setEditingPartId(part.id);
    setEditingName(part.name);
  };

  const handleSaveRename = (id: string) => {
    if (editingName.trim()) {
      renamePart(id, editingName.trim());
    }
    setEditingPartId(null);
  };

  const renderTreeNodes = () =>
    parts.map((part) => {
      const isSelected = selectedNodeId === part.id;
      const isEditing = editingPartId === part.id;

      return (
        <div key={part.id} className="space-y-1">
          <div
            onClick={() => selectNode(part.id)}
            className={`flex items-center justify-between py-2 px-2.5 rounded-xl text-xs cursor-pointer transition-colors ${
              isSelected
                ? 'bg-indigo-50 text-indigo-700 font-bold border border-indigo-200'
                : 'hover:bg-slate-100 text-slate-700 border border-transparent'
            }`}
          >
            <div className="flex items-center space-x-2 truncate flex-1 mr-2">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: part.color || '#6366f1' }}
              />
              {isEditing ? (
                <div className="flex items-center space-x-1 flex-1" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="text"
                    value={editingName}
                    onChange={(e) => setEditingName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveRename(part.id);
                      if (e.key === 'Escape') setEditingPartId(null);
                    }}
                    autoFocus
                    className="bg-white border border-indigo-300 rounded px-1.5 py-0.5 text-xs text-slate-800 outline-none w-full"
                  />
                  <button
                    onClick={() => handleSaveRename(part.id)}
                    className="p-0.5 text-emerald-600 hover:text-emerald-700"
                  >
                    <Check className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => setEditingPartId(null)}
                    className="p-0.5 text-slate-400 hover:text-slate-600"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ) : (
                <span className="truncate">{part.name}</span>
              )}
            </div>

            {!isEditing && (
              <div className="flex items-center space-x-1 opacity-80 shrink-0">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleStartRename(part);
                  }}
                  title="Rename part"
                  className="p-1 text-slate-400 hover:text-indigo-600 rounded transition-colors"
                >
                  <Edit2 className="w-3 h-3" />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    togglePartVisibility(part.id);
                  }}
                  title={part.visible ? 'Hide part' : 'Show part'}
                  className="p-1 text-slate-400 hover:text-slate-700 rounded transition-colors"
                >
                  {part.visible ? <Eye className="w-3 h-3 text-indigo-500" /> : <EyeOff className="w-3 h-3 text-slate-300" />}
                </button>
                {parts.length > 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removePart(part.id);
                    }}
                    title="Delete part"
                    className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      );
    });

  if (inspectorTab === 'tree') {
    return (
      <div className="flex-1 flex flex-col">
        <div className="flex border-b border-slate-200 bg-slate-50/50 p-1.5">
          <button
            onClick={() => setInspectorTab('inspector')}
            className="flex-1 py-2 font-bold text-center rounded-xl text-slate-500 hover:text-slate-900 transition-all text-xs"
          >
            Properties
          </button>
          <button className="flex-1 py-2 font-bold text-center rounded-xl bg-white text-indigo-600 shadow-xs border border-slate-200 text-xs">
            Model Tree
          </button>
        </div>

        <div className="p-4 flex-1 space-y-4 overflow-y-auto">
          <div className="flex items-center justify-between text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
            <span>Model Hierarchy ({parts.length} parts)</span>
            <Layers className="w-3.5 h-3.5 text-slate-400" />
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => addNewPart()}
              className="flex-1 flex items-center justify-center space-x-1.5 py-2 px-3 rounded-xl text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition-all shadow-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Part</span>
            </button>

            <button
              onClick={toggleAssemblyMode}
              title={assemblyMode ? 'Assembly Mode Active' : 'Enable Assembly Mode'}
              className={`py-2 px-3 rounded-xl text-xs font-bold transition-all border ${
                assemblyMode
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                  : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
              }`}
            >
              {assemblyMode ? 'Assembly On' : 'Assemble'}
            </button>
          </div>

          <div className="space-y-1 bg-slate-50/50 border border-slate-200 rounded-2xl p-2 min-h-[160px]">
            {parts.length === 0 ? (
              <p className="text-xs text-slate-400 font-mono p-4 text-center">
                No parts in model.<br />Click "+ Add Part" to create one.
              </p>
            ) : (
              renderTreeNodes()
            )}
          </div>

          {selectedPart && (
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-800">Selected: {selectedPart.name}</span>
                <span
                  className="text-[10px] font-mono px-2 py-0.5 rounded-md text-white font-bold"
                  style={{ backgroundColor: selectedPart.color || '#6366f1' }}
                >
                  Active Part
                </span>
              </div>
              <p className="text-[11px] text-slate-500">
                Switch to the <strong>Properties</strong> tab to edit this part's dimensions and relative offset.
              </p>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex border-b border-slate-200 bg-slate-50/50 p-1.5">
        <button className="flex-1 py-2 font-bold text-center rounded-xl bg-white text-indigo-600 shadow-xs border border-slate-200 text-xs">
          Properties
        </button>
        <button
          onClick={() => setInspectorTab('tree')}
          className="flex-1 py-2 font-bold text-center rounded-xl text-slate-500 hover:text-slate-900 transition-all text-xs"
        >
          Model Tree ({parts.length})
        </button>
      </div>

      <div className="p-4 space-y-6 flex-1 overflow-y-auto">

        {/* ACTIVE PART BADGE */}
        {selectedPart && (
          <div className="flex items-center justify-between bg-indigo-50/60 border border-indigo-200 rounded-xl px-3 py-2">
            <div className="flex items-center space-x-2 truncate">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: selectedPart.color || '#6366f1' }}
              />
              <span className="font-sans font-bold text-indigo-950 text-xs truncate">
                {selectedPart.name}
              </span>
            </div>
            <div className="flex items-center space-x-2">
              {parts.length > 1 && (
                <button
                  onClick={() => {
                    if (window.confirm(`Are you sure you want to delete "${selectedPart.name}"?`)) {
                      removePart(selectedPart.id);
                    }
                  }}
                  title="Delete part"
                  className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
              <button
                onClick={() => setInspectorTab('tree')}
                className="text-[10px] font-mono text-indigo-600 hover:text-indigo-800 font-bold shrink-0"
              >
                Switch Part
              </button>
            </div>
          </div>
        )}

        {/* 3D BOUNDING DIMENSIONS */}
        <div className="space-y-3">
          <div className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400">
            {selectedPart ? `${selectedPart.name} Dimensions` : '3D Bounding Dimensions'}
          </div>
          <div className="space-y-2">
            {[
              {
                key: 'length',
                label: 'Length (L)',
                val: selectedPart?.dimensions?.length ?? length,
                set: (v: number) => {
                  setLength(v);
                  if (selectedPart) updatePartDimensions(selectedPart.id, { length: v });
                },
                err: inputErrors.length
              },
              {
                key: 'width',
                label: 'Width (W)',
                val: selectedPart?.dimensions?.width ?? width,
                set: (v: number) => {
                  setWidth(v);
                  if (selectedPart) updatePartDimensions(selectedPart.id, { width: v });
                },
                err: inputErrors.width
              },
              {
                key: 'height',
                label: 'Height (H)',
                val: selectedPart?.dimensions?.height ?? height,
                set: (v: number) => {
                  setHeight(v);
                  if (selectedPart) updatePartDimensions(selectedPart.id, { height: v });
                },
                err: inputErrors.height
              },
            ].map(({ key, label, val, set: setter, err }) => (
              <div key={key} className="space-y-1">
                <div className={`flex items-center justify-between border rounded-xl px-3 py-2 ${err ? 'bg-rose-50 border-rose-300' : 'bg-slate-50 border-slate-200'}`}>
                  <span className="font-sans text-slate-600 font-bold text-xs">{label} <span className="text-rose-500">*</span></span>
                  <div className="flex items-center space-x-1 font-mono font-semibold text-slate-900">
                    <input
                      key={`${selectedNodeId ?? 'none'}-${key}`}
                      type="number"
                      min="0.1"
                      step="1"
                      defaultValue={val}
                      onBlur={(e) => setter(parseFloat(e.target.value) || 0)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') setter(parseFloat((e.target as HTMLInputElement).value) || 0);
                      }}
                      className="bg-transparent text-right outline-none w-20 text-slate-900 font-bold text-xs"
                    />
                    <span className="text-[10px] text-slate-400">mm</span>
                  </div>
                </div>
                {err && <p className="text-[10px] font-bold text-rose-600 px-1 font-mono">{err}</p>}
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};

// ── Main PropertiesInspector ──────────────────────────────────────────────────
export const PropertiesInspector: React.FC = () => {
  const { viewMode } = useWorkspaceStore();
  const is3D = viewMode === 'workspace_3d';

  return (
    <aside className="w-64 lg:w-72 bg-white border-l border-slate-200/90 flex flex-col select-none font-sans text-xs shrink-0 z-30 overflow-hidden">
      <div className="flex items-center px-4 py-3 border-b border-slate-200 bg-slate-50/50 shrink-0">
        <div className="flex items-center space-x-2">
          {is3D ? <Box className="w-4 h-4 text-indigo-500" /> : <FileCode className="w-4 h-4 text-emerald-500" />}
          <span className="font-bold text-slate-800 text-xs">{is3D ? '3D Properties Inspector' : '2D Properties Inspector'}</span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {is3D ? <Inspector3D /> : <Inspector2D />}
      </div>
    </aside>
  );
};
