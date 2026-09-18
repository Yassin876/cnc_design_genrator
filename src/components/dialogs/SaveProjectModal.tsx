import React, { useState, useEffect } from 'react';
import { X, FolderPlus, Sparkles, Check } from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { projectsApiService } from '../../services/api/projects';

interface SaveProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultType?: '2D' | '3D';
  filePath?: string;
  onSaved?: (projectId: string, projectName: string) => void;
}

export const SaveProjectModal: React.FC<SaveProjectModalProps> = ({
  isOpen,
  onClose,
  defaultType = '3D',
  filePath,
  onSaved
}) => {
  const { viewMode, activeProjectId, setActiveProjectId } = useWorkspaceStore();
  const currentType = defaultType || (viewMode === 'workspace_2d' ? '2D' : '3D');

  const generateDefaultName = () => {
    const now = new Date();
    const dateStr = now.toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    return `Untitled ${currentType} Project (${dateStr})`;
  };

  const [projectName, setProjectName] = useState(generateDefaultName());
  const [description, setDescription] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setProjectName(generateDefaultName());
      setError(null);
    }
  }, [isOpen, currentType]);

  if (!isOpen) return null;

  const handleSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const finalName = projectName.trim() || generateDefaultName();
    setIsSaving(true);
    setError(null);

    try {
      const created = await projectsApiService.createProject({
        name: finalName,
        description: description.trim() || `Created from ${currentType} Workspace generation`,
        type: currentType,
        file_path: filePath
      });

      setActiveProjectId(created.id, created.name);
      if (onSaved) {
        onSaved(created.id, created.name);
      }
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to save project. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 select-none font-sans">
      <div className="bg-white border border-slate-200 w-full max-w-md rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center space-x-2 text-slate-900 font-bold text-sm">
            <div className="w-8 h-8 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600">
              <FolderPlus className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Name Your Project</h3>
              <p className="text-[11px] text-slate-400 font-normal">Save this CAD generation to your workspace</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSave} className="p-5 space-y-4">
          {error && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 font-medium">
              {error}
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 flex items-center justify-between">
              <span>Project Name</span>
              <span className="text-[10px] text-indigo-600 font-semibold">{currentType} Model</span>
            </label>
            <input
              type="text"
              autoFocus
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="e.g. Mechanical Gear Adapter"
              className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all font-medium"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700">Description (Optional)</label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Notes, target material, machine specs..."
              className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all resize-none"
            />
          </div>

          <div className="pt-2 flex items-center justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 rounded-xl hover:bg-slate-100 transition-colors"
            >
              Skip
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-sm transition-all flex items-center space-x-1.5"
            >
              {isSaving ? (
                <span>Saving...</span>
              ) : (
                <>
                  <Check className="w-3.5 h-3.5 ml-1" />
                  <span>Save Project</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
