import React, { useState, useEffect } from 'react';
import { Download, CheckCircle2, X, Settings2 } from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { use2DWorkspaceStore } from '../../app/store/use2DWorkspaceStore';
import { use3DWorkspaceStore } from '../../app/store/use3DWorkspaceStore';
import { cadService } from '../../services/cad/cadService';

export const ExportDialog: React.FC = () => {
  const { isExportModalOpen, setExportModalOpen, viewMode, units } = useWorkspaceStore();
  const is3D = viewMode === 'workspace_3d';

  const store2D = use2DWorkspaceStore();
  const store3D = use3DWorkspaceStore();
  const activeFilePath = is3D ? store3D.activeFilePath : store2D.activeFilePath;

  type Format3D = 'STL' | 'STEP' | 'OBJ';
  const [selectedFormat3D, setSelectedFormat3D] = useState<Format3D>('STL');

  const [stlMode, setStlMode] = useState<'binary' | 'ascii'>('binary');
  const [meshResolution, setMeshResolution] = useState<'high' | 'medium' | 'low'>('high');
  const [dxfVersion, setDxfVersion] = useState<'R12' | 'R2000' | 'R2018'>('R2018');

  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    setSelectedFormat3D('STL');
    setExportSuccess(null);
    setExportError(null);
  }, [viewMode, isExportModalOpen]);

  if (!isExportModalOpen) return null;

  const selectedFormat = is3D ? selectedFormat3D : 'DXF';

  const handleExecuteExport = async () => {
    setIsExporting(true);
    setExportSuccess(null);
    setExportError(null);

    try {
      if (!activeFilePath) throw new Error('No file loaded. Generate a model first before exporting.');
      const ext = selectedFormat.toLowerCase();
      const baseName = activeFilePath.split(/[/\\]/).pop() || '';
      const stem = baseName.substring(0, baseName.lastIndexOf('.')) || baseName;
      const defaultFileName = `${stem}.${ext}`;

      let destPath = `C:\\Users\\Public\\Exports\\${defaultFileName}`;
      if ((window as any).electronAPI?.saveFileDialog) {
        const nativePath = await (window as any).electronAPI.saveFileDialog(defaultFileName);
        if (!nativePath) { setIsExporting(false); return; }
        destPath = nativePath;
      }

      await cadService.exportModel(activeFilePath, ext, destPath, { stlMode, meshResolution, dxfVersion, units });
      setExportSuccess(`✅ Saved to: ${destPath}`);
      setTimeout(() => { setExportModalOpen(false); }, 2500);
    } catch (err: any) {
      console.error('Export error:', err);
      setExportError(err.message || 'Export operation failed');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-md flex items-center justify-center p-4 select-none font-sans">
      <div className="bg-white border border-slate-200 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-white">
          <div className="flex items-center space-x-2 font-bold text-sm text-slate-900">
            <Download className="w-5 h-5 text-indigo-600" />
            <span>Export {is3D ? `3D Model — ${selectedFormat}` : '2D Blueprint — DXF'}</span>
          </div>
          <button
            onClick={() => setExportModalOpen(false)}
            className="text-slate-400 hover:text-slate-700 p-1 rounded-lg hover:bg-slate-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 space-y-4">
          
          {/* Format Selector only for 3D */}
          {is3D && (
            <div>
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-2">
                Output Format (3D Standard)
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedFormat3D('STL')}
                  className="flex-1 p-3 rounded-xl border font-mono font-bold text-sm bg-indigo-50 border-indigo-300 text-indigo-700 shadow-sm"
                >
                  STL (3D Mesh)
                </button>
              </div>
            </div>
          )}

          {/* Format Settings */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3 font-mono text-xs">
            <div className="flex items-center space-x-1.5 font-bold text-slate-900 text-xs border-b border-slate-200 pb-2">
              <Settings2 className="w-4 h-4 text-indigo-600" />
              <span>{is3D ? `${selectedFormat} Output Settings` : 'DXF Output Settings'}</span>
            </div>

            {is3D && selectedFormat === 'STL' && (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-slate-600">Encoding:</span>
                  <div className="flex bg-white p-0.5 rounded-lg border border-slate-200">
                    <button
                      onClick={() => setStlMode('binary')}
                      className={`px-2.5 py-1 rounded text-[10px] font-bold ${stlMode === 'binary' ? 'bg-indigo-600 text-white' : 'text-slate-600'}`}
                    >
                      Binary (Standard)
                    </button>
                    <button
                      onClick={() => setStlMode('ascii')}
                      className={`px-2.5 py-1 rounded text-[10px] font-bold ${stlMode === 'ascii' ? 'bg-indigo-600 text-white' : 'text-slate-600'}`}
                    >
                      ASCII
                    </button>
                  </div>
                </div>
              </div>
            )}

            {!is3D && (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-slate-600">DXF Specification:</span>
                  <select
                    value={dxfVersion}
                    onChange={(e) => setDxfVersion(e.target.value as any)}
                    className="bg-white border border-slate-200 text-slate-900 text-xs rounded px-2.5 py-1 outline-none"
                  >
                    <option value="R2018">AutoCAD 2018 / 2024 DXF</option>
                    <option value="R2000">AutoCAD 2000 DXF</option>
                    <option value="R12">AutoCAD R12 (Legacy CNC)</option>
                  </select>
                </div>
              </div>
            )}

            <div className="flex justify-between items-center border-t border-slate-200 pt-2 text-[11px]">
              <span className="text-slate-600">Unit System:</span>
              <span className="text-indigo-600 font-bold">{units.toUpperCase()}</span>
            </div>
          </div>

          {exportSuccess && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs flex items-center space-x-2 font-mono">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{exportSuccess}</span>
            </div>
          )}

          {exportError && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded-xl text-xs flex items-center space-x-2 font-mono">
              <X className="w-4 h-4 shrink-0" />
              <span>{exportError}</span>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-white flex items-center justify-end space-x-3">
          <button
            onClick={() => setExportModalOpen(false)}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl"
          >
            Cancel
          </button>

          <button
            onClick={handleExecuteExport}
            disabled={isExporting}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-md shadow-indigo-600/20 flex items-center space-x-2 transition-all disabled:opacity-50"
          >
            {isExporting ? (
              <span>Saving {selectedFormat}...</span>
            ) : (
              <>
                <Download className="w-4 h-4" />
                <span>Export {selectedFormat}</span>
              </>
            )}
          </button>
        </div>

      </div>
    </div>
  );
};
