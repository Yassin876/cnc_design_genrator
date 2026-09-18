import React, { useState } from 'react';
import { X, Sparkles, Image as ImageIcon, Box, FileText, UploadCloud, ArrowRight, AlertCircle } from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { useAuthStore } from '../../app/store/useAuthStore';
import { projectsApiService } from '../../services/api/projects';

export const NewProjectDialog: React.FC = () => {
  const { isNewProjectModalOpen, setNewProjectModalOpen, setViewMode, setImportModalOpen } = useWorkspaceStore();
  const { user } = useAuthStore();

  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  if (!isNewProjectModalOpen) return null;

  const createProjectAndNavigate = async (
    name: string,
    projectType: '2D' | '3D',
    navigateTo: 'workspace_2d' | 'workspace_3d'
  ) => {
    setIsCreating(true);
    setCreateError(null);
    try {
      await projectsApiService.createProject({
        name,
        description: `New ${projectType} project created via Quick Start`,
        type: projectType
      });
      setViewMode(navigateTo);
      setNewProjectModalOpen(false);
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create project');
    } finally {
      setIsCreating(false);
    }
  };

  const creationModes = [
    {
      id: 'text_to_3d',
      title: 'Text Prompt → 3D Model',
      desc: 'Generate parametric 3D CAD mesh directly from industrial text prompts.',
      icon: <Sparkles className="w-6 h-6 text-violet-400" />,
      action: () => createProjectAndNavigate('New 3D AI Design', '3D', 'workspace_3d')
    },
    {
      id: 'image_to_3d',
      title: 'Image → 3D CAD Model',
      desc: 'Convert 2D engineering sketches or photographs into extruded 3D solids.',
      icon: <ImageIcon className="w-6 h-6 text-cyan-400" />,
      action: () => createProjectAndNavigate('New 3D Image Design', '3D', 'workspace_3d')
    },
    {
      id: 'model_ai_edit',
      title: '3D Model AI Parametric Edit',
      desc: 'Load existing 3D mesh and perform AI-driven contextual feature modifications.',
      icon: <Box className="w-6 h-6 text-emerald-400" />,
      action: () => createProjectAndNavigate('New 3D Parametric Design', '3D', 'workspace_3d')
    },
    {
      id: 'text_to_2d',
      title: 'Text Prompt → 2D Blueprint',
      desc: 'Synthesize standard 2D vector DXF blueprints with dimension lines.',
      icon: <FileText className="w-6 h-6 text-amber-400" />,
      action: () => createProjectAndNavigate('New 2D Blueprint', '2D', 'workspace_2d')
    },
    {
      id: 'image_to_2d',
      title: 'Image / File → 2D Vector',
      desc: 'Vectorize raster images or CAD drawings into multi-layer DXF paths.',
      icon: <ImageIcon className="w-6 h-6 text-pink-400" />,
      action: () => createProjectAndNavigate('New 2D Vector Design', '2D', 'workspace_2d')
    },
    {
      id: 'import_cad',
      title: 'Import Existing CAD Asset',
      desc: 'Import raw STEP, STL, OBJ, DXF files for inspection and CAM nesting.',
      icon: <UploadCloud className="w-6 h-6 text-blue-400" />,
      action: () => {
        setNewProjectModalOpen(false);
        setImportModalOpen(true);
      }
    }
  ];

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 select-none font-sans">
      <div className="bg-cad-panel border border-cad-border w-full max-w-4xl rounded-2xl shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="p-4 border-b border-cad-border flex items-center justify-between bg-cad-panel">
          <div className="flex items-center space-x-2 font-bold text-sm text-white">
            <Sparkles className="w-5 h-5 text-violet-400" />
            <span>Create New CNC Project</span>
          </div>
          <button
            onClick={() => setNewProjectModalOpen(false)}
            className="text-cad-textMuted hover:text-white p-1 rounded-lg hover:bg-cad-surface"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Error Banner */}
        {createError && (
          <div className="mx-6 mt-4 p-3 bg-rose-950/60 border border-rose-800 text-rose-300 rounded-xl text-xs flex items-center space-x-2 font-mono">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{createError}</span>
          </div>
        )}

        {/* Modes Grid */}
        <div className="p-6 grid grid-cols-2 gap-4 max-h-[70vh] overflow-y-auto">
          {creationModes.map((mode) => (
            <div
              key={mode.id}
              onClick={isCreating ? undefined : mode.action}
              className={`group bg-cad-surface hover:bg-cad-card border border-cad-border hover:border-violet-500 p-5 rounded-2xl cursor-pointer transition-all flex items-start space-x-4 shadow-sm ${isCreating ? 'opacity-60 pointer-events-none' : ''}`}
            >
              <div className="p-3 bg-cad-bg rounded-xl border border-cad-border group-hover:scale-110 transition-transform">
                {mode.icon}
              </div>

              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-white group-hover:text-violet-300 transition-colors">
                    {mode.title}
                  </h4>
                  <ArrowRight className="w-4 h-4 text-cad-textMuted opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                </div>
                <p className="text-xs text-cad-textMuted leading-relaxed">
                  {mode.desc}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-cad-border bg-cad-panel flex items-center justify-between">
          <span className="text-[11px] text-cad-textMuted font-mono">
            {user ? `Signed in as ${user.email}` : 'Not signed in'}
          </span>
          <button
            onClick={() => setNewProjectModalOpen(false)}
            className="px-5 py-2 bg-cad-surface hover:bg-cad-card text-cad-textMuted text-xs font-bold rounded-xl"
          >
            Cancel
          </button>
        </div>

      </div>
    </div>
  );
};
