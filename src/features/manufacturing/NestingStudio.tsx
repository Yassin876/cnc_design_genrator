import React, { useState } from 'react';
import { Layers3, Play, Download, Settings, FileText, CheckCircle2, RotateCw, Sparkles, Layers } from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { use2DWorkspaceStore } from '../../app/store/use2DWorkspaceStore';
import { cadService } from '../../services/cad/cadService';
import { NestResult } from '../../types';

export const NestingStudio: React.FC = () => {
  const { loadFile, activeFilePath } = useWorkspaceStore();
  const store2D = use2DWorkspaceStore();

  const [sheetWidth, setSheetWidth] = useState<number>(1200);
  const [sheetHeight, setSheetHeight] = useState<number>(600);
  const [sheetThickness, setSheetThickness] = useState<number>(18);
  const [spacing, setSpacing] = useState<number>(5.0);
  const [allowRotate, setAllowRotate] = useState<boolean>(true);
  const [isNesting, setIsNesting] = useState<boolean>(false);
  const [nestResult, setNestResult] = useState<NestResult | null>(null);
  const [nestError, setNestError] = useState<string | null>(null);

  const currentPartPath = store2D.activeFilePath || activeFilePath;

  const handleRunNesting = async () => {
    if (!currentPartPath) {
      setNestError('Load a 2D DXF part in the workspace before running nesting.');
      return;
    }

    setIsNesting(true);
    setNestError(null);
    try {
      const res = await cadService.runNesting(
        [currentPartPath],
        sheetWidth,
        sheetHeight,
        spacing,
        allowRotate,
        sheetThickness
      );
      setNestResult(res);
      const nestedPath = res.sheets?.[0]?.dxf_path;
      if (nestedPath) {
        store2D.setActiveFile(nestedPath);
        loadFile(nestedPath, '2D');
      }
    } catch (err: any) {
      console.error('Nesting failed:', err);
      const detail = err?.response?.data?.detail || err?.message || 'Nesting operation failed';
      setNestError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setIsNesting(false);
    }
  };

  return (
    <div className="flex-1 bg-cad-bg overflow-y-auto p-8 select-none font-sans">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-cad-border pb-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-amber-950/80 border border-amber-700/50 flex items-center justify-center text-amber-400 shadow-lg">
              <Layers3 className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                CNC Nesting Studio
                <span className="text-xs font-mono bg-amber-950 text-amber-300 border border-amber-800 px-2 py-0.5 rounded">
                  Multi-Sheet Inventory
                </span>
              </h1>
              <p className="text-xs text-cad-textMuted font-mono">Pack 2D DXF profiles onto stock sheet inventory with rectpack optimization</p>
            </div>
          </div>

          <button
            onClick={handleRunNesting}
            disabled={isNesting}
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white font-bold text-xs flex items-center space-x-2 shadow-lg shadow-amber-600/20 transition-all"
          >
            <Play className="w-4 h-4 fill-white" />
            <span>{isNesting ? 'Calculating Optimal Nesting...' : 'Run Nesting Optimizer'}</span>
          </button>
        </div>

        {/* Top Controls Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          
          {/* Stock Sheet Config */}
          <div className="bg-cad-panel border border-cad-border p-5 rounded-xl space-y-3">
            <h3 className="text-xs font-mono font-bold text-white uppercase tracking-wider flex items-center space-x-2">
              <Settings className="w-4 h-4 text-amber-400" />
              <span>Stock Sheet Parameters</span>
            </h3>

            <div className="space-y-2 text-xs font-mono">
              <div>
                <span className="text-cad-textMuted block mb-1">Sheet Width (X mm)</span>
                <input
                  type="number"
                  value={sheetWidth}
                  onChange={(e) => setSheetWidth(parseFloat(e.target.value))}
                  className="w-full bg-cad-surface border border-cad-border text-white p-2 rounded-lg"
                />
              </div>

              <div>
                <span className="text-cad-textMuted block mb-1">Sheet Height (Y mm)</span>
                <input
                  type="number"
                  value={sheetHeight}
                  onChange={(e) => setSheetHeight(parseFloat(e.target.value))}
                  className="w-full bg-cad-surface border border-cad-border text-white p-2 rounded-lg"
                />
              </div>

              <div>
                <span className="text-cad-textMuted block mb-1">Sheet Thickness (mm)</span>
                <input
                  type="number"
                  value={sheetThickness}
                  onChange={(e) => setSheetThickness(parseFloat(e.target.value))}
                  className="w-full bg-cad-surface border border-cad-border text-white p-2 rounded-lg"
                />
              </div>
            </div>
          </div>

          {/* CNC Spacing & Rotation */}
          <div className="bg-cad-panel border border-cad-border p-5 rounded-xl space-y-3">
            <h3 className="text-xs font-mono font-bold text-white uppercase tracking-wider flex items-center space-x-2">
              <RotateCw className="w-4 h-4 text-cyan-400" />
              <span>CNC Tool & Rotation Controls</span>
            </h3>

            <div className="space-y-3 text-xs font-mono">
              <div>
                <span className="text-cad-textMuted block mb-1">Part-to-Part Clearance (mm)</span>
                <input
                  type="number"
                  value={spacing}
                  onChange={(e) => setSpacing(parseFloat(e.target.value))}
                  className="w-full bg-cad-surface border border-cad-border text-white p-2 rounded-lg"
                />
              </div>

              <label className="flex items-center space-x-2 pt-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={allowRotate}
                  onChange={(e) => setAllowRotate(e.target.checked)}
                  className="accent-amber-500 w-4 h-4 rounded"
                />
                <span className="text-cad-textMain">Allow 90° Part Rotation</span>
              </label>
            </div>
          </div>

          {/* Parts Queue */}
          <div className="bg-cad-panel border border-cad-border p-5 rounded-xl space-y-3">
            <h3 className="text-xs font-mono font-bold text-white uppercase tracking-wider flex items-center space-x-2">
              <FileText className="w-4 h-4 text-violet-400" />
              <span>DXF Parts Queue ({currentPartPath ? 1 : 0})</span>
            </h3>

            <div className="space-y-1.5 font-mono text-xs max-h-32 overflow-y-auto">
              {currentPartPath ? (
                <div className="p-2 bg-cad-surface border border-cad-border rounded-lg text-cad-textMain flex items-center justify-between">
                  <span className="truncate">{currentPartPath.split(/[/\\]/).pop()}</span>
                  <span className="text-[10px] text-amber-400 font-bold">Qty: 1</span>
                </div>
              ) : (
                <p className="text-cad-textMuted">No DXF loaded. Generate or open a 2D part first.</p>
              )}
            </div>
          </div>

        </div>

        {nestError && (
          <div className="bg-red-950/60 border border-red-800 rounded-xl p-4 text-xs font-mono text-red-200">
            {nestError}
          </div>
        )}

        {/* Nesting Results Section */}
        {nestResult && (
          <div className="bg-cad-panel border border-cad-border p-6 rounded-2xl space-y-6">
            <div className="flex items-center justify-between border-b border-cad-border pb-4">
              <div className="flex items-center space-x-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <h3 className="font-bold text-white text-base">Nesting Optimization Results</h3>
              </div>
              <span className="text-xs font-mono text-emerald-400 bg-emerald-950 px-3 py-1 rounded-full border border-emerald-800 font-bold">
                {nestResult.total_utilization.toFixed(1)}% Sheet Utilization
              </span>
            </div>

            <div className="grid grid-cols-4 gap-4 text-center font-mono">
              <div className="bg-cad-surface p-4 rounded-xl border border-cad-border">
                <span className="text-cad-textMuted text-xs block">Parts Placed</span>
                <span className="text-xl font-bold text-white">{nestResult.total_parts_placed} / {nestResult.total_parts_required}</span>
              </div>
              <div className="bg-cad-surface p-4 rounded-xl border border-cad-border">
                <span className="text-cad-textMuted text-xs block">Stock Sheets Used</span>
                <span className="text-xl font-bold text-amber-400">{nestResult.total_sheets_used}</span>
              </div>
              <div className="bg-cad-surface p-4 rounded-xl border border-cad-border">
                <span className="text-cad-textMuted text-xs block">Material Utilization</span>
                <span className="text-xl font-bold text-emerald-400">{nestResult.total_utilization.toFixed(1)}%</span>
              </div>
              <div className="bg-cad-surface p-4 rounded-xl border border-cad-border">
                <span className="text-cad-textMuted text-xs block">Scrap Waste</span>
                <span className="text-xl font-bold text-violet-400">{nestResult.total_waste.toFixed(1)}%</span>
              </div>
            </div>

            {/* Generated Nested Sheet Layouts */}
            <div className="space-y-3">
              <h4 className="text-xs font-mono font-bold text-cad-textMuted uppercase tracking-wider">
                Production Sheets Output
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {nestResult.sheets.map((sheet, i) => (
                  <div key={i} className="bg-cad-surface border border-cad-border p-4 rounded-xl space-y-3">
                    <div className="flex justify-between items-center font-mono text-xs">
                      <span className="font-bold text-white">{sheet.sheet_name}</span>
                      <span className="text-emerald-400">{sheet.utilization.toFixed(1)}% used</span>
                    </div>

                    <div className="h-40 bg-cad-bg rounded-lg border border-cad-border flex items-center justify-center relative overflow-hidden">
                      <div className="absolute inset-4 border border-dashed border-amber-500/40 rounded flex items-center justify-center">
                        <span className="text-xs font-mono text-amber-300">Nested DXF Layout View</span>
                      </div>
                    </div>

                    <button
                      onClick={() => {
                        store2D.setActiveFile(sheet.dxf_path);
                        loadFile(sheet.dxf_path, '2D');
                      }}
                      className="w-full py-2 bg-cad-panel hover:bg-cad-card border border-cad-border text-white text-xs font-mono rounded-lg flex items-center justify-center space-x-1.5"
                    >
                      <Layers className="w-3.5 h-3.5 text-amber-400" />
                      <span>Open Sheet DXF in 2D Viewport</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>

          </div>
        )}

      </div>
    </div>
  );
};
