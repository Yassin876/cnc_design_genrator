import React, { useState } from 'react';
import { X, UploadCloud, FileCode, CheckCircle2, AlertCircle, Box } from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { cadService } from '../../services/cad/cadService';

export const ImportDialog: React.FC = () => {
  const { isImportModalOpen, setImportModalOpen, loadFile, setInspectionData } = useWorkspaceStore();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [localPath, setLocalPath] = useState<string>('');
  const [isImporting, setIsImporting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isImportModalOpen) return null;

  const handleNativeOpen = async () => {
    try {
      if (window.electronAPI?.openFileDialog) {
        const filePath = await window.electronAPI.openFileDialog();
        if (filePath) {
          setLocalPath(filePath);
        }
      }
    } catch (err: any) {
      console.error('Native dialog error:', err);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleExecuteImport = async () => {
    setIsImporting(true);
    setError(null);

    try {
      let targetPath = localPath;

      if (selectedFile) {
        const formData = new FormData();
        formData.append('file', selectedFile);

        const res = await fetch('http://127.0.0.1:8000/api/v1/files/upload', {
          method: 'POST',
          body: formData
        });

        if (!res.ok) throw new Error('Failed to upload file to backend server');
        const data = await res.json();
        targetPath = data.saved_path;
      }

      if (!targetPath) {
        throw new Error('Please select a file to import');
      }

      const ext = targetPath.split('.').pop()?.toLowerCase();
      const is2D = ext === 'dxf' || ext === 'svg' || ext === 'png' || ext === 'jpg';

      if (!is2D && (ext === 'stl' || ext === 'obj')) {
        const inspect = await cadService.inspect3D(targetPath);
        setInspectionData(inspect);
      }

      loadFile(targetPath, is2D ? '2D' : '3D');
      setImportModalOpen(false);
    } catch (err: any) {
      setError(err.message || 'Import failed');
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 select-none font-sans">
      <div className="bg-white border border-slate-200/90 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">

        {/* Header */}
        <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600 font-bold">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-slate-900">Import CAD / Drawing File</h3>
              <p className="text-xs text-slate-500">Load 3D STL models or 2D DXF drawings into workspace</p>
            </div>
          </div>
          <button
            onClick={() => setImportModalOpen(false)}
            className="text-slate-400 hover:text-slate-700 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">

          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl text-xs flex items-start space-x-2 font-mono">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Desktop File Picker */}
          {window.electronAPI?.openFileDialog && (
            <button
              type="button"
              onClick={handleNativeOpen}
              className="w-full py-3 px-4 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold rounded-xl flex items-center justify-center space-x-2 transition-colors"
            >
              <Box className="w-4 h-4 text-indigo-600" />
              <span>Select via Native File Manager</span>
            </button>
          )}

          {localPath && (
            <div className="p-3 bg-indigo-50/60 border border-indigo-200 rounded-xl text-xs font-mono text-indigo-800 truncate">
              Selected Path: {localPath}
            </div>
          )}

          {/* Drag & Drop File Zone */}
          <div className="relative border-2 border-dashed border-indigo-200 hover:border-indigo-500 rounded-2xl p-6 text-center bg-indigo-50/30 transition-colors">
            <UploadCloud className="w-10 h-10 text-indigo-600 mx-auto mb-2" />
            <p className="text-xs text-slate-800 font-bold mb-1">
              Drag & Drop file here or click to browse
            </p>
            <p className="text-[11px] text-slate-400 font-mono">
              Supported Formats: STL, OBJ, GLB, STEP, DXF, PNG, JPG
            </p>
            <input
              type="file"
              onChange={handleFileChange}
              accept=".stl,.obj,.glb,.step,.stp,.dxf,.svg,.png,.jpg,.jpeg"
              className="absolute inset-0 opacity-0 cursor-pointer"
            />
          </div>

          {selectedFile && (
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between text-xs font-mono">
              <div className="flex items-center space-x-2 truncate">
                <FileCode className="w-4 h-4 text-indigo-600 shrink-0" />
                <span className="text-slate-800 font-bold truncate">{selectedFile.name}</span>
              </div>
              <span className="text-slate-400 shrink-0">
                {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </span>
            </div>
          )}

          {/* Supported Format Badges */}
          <div className="grid grid-cols-4 gap-2 pt-2 border-t border-slate-100 text-center font-mono text-[10px]">
            <div className="bg-slate-50 p-2 rounded-xl border border-slate-200">
              <span className="text-indigo-600 font-bold block">3D MESH</span>
              <span className="text-slate-400">STL / OBJ</span>
            </div>
            <div className="bg-slate-50 p-2 rounded-xl border border-slate-200">
              <span className="text-blue-600 font-bold block">NURBS CAD</span>
              <span className="text-slate-400">STEP / STP</span>
            </div>
            <div className="bg-slate-50 p-2 rounded-xl border border-slate-200">
              <span className="text-emerald-600 font-bold block">2D VECTOR</span>
              <span className="text-slate-400">DXF / SVG</span>
            </div>
            <div className="bg-slate-50 p-2 rounded-xl border border-slate-200">
              <span className="text-violet-600 font-bold block">IMAGE</span>
              <span className="text-slate-400">PNG / JPG</span>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="p-5 border-t border-slate-100 bg-slate-50/50 flex items-center justify-end space-x-3">
          <button
            onClick={() => setImportModalOpen(false)}
            className="px-4 py-2.5 bg-white border border-slate-200 hover:bg-slate-100 text-slate-600 text-xs font-bold rounded-xl transition-colors"
          >
            Cancel
          </button>

          <button
            onClick={handleExecuteImport}
            disabled={isImporting || (!selectedFile && !localPath)}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-lg shadow-indigo-600/20 flex items-center space-x-2 disabled:opacity-50 transition-all"
          >
            {isImporting ? (
              <span>Importing Model...</span>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                <span>Load Into Workspace</span>
              </>
            )}
          </button>
        </div>

      </div>
    </div>
  );
};
