import React, { useState, useEffect } from 'react';
import { History, RotateCcw, Copy, Clock, CheckCircle2, Layers, X, AlertCircle } from 'lucide-react';
import { useProjectStore } from '../../app/store/useProjectStore';
import { useModelStore } from '../../app/store/useModelStore';
import { projectService } from '../../services/projects/projectService';
import { ProjectVersion } from '../../types';

interface VersionHistoryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const VersionHistoryModal: React.FC<VersionHistoryModalProps> = ({ isOpen, onClose }) => {
  const { activeProject } = useProjectStore();
  const { setParameters } = useModelStore();

  const [versions, setVersions] = useState<ProjectVersion[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<ProjectVersion | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isActing, setIsActing] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadVersions();
    }
  }, [isOpen, activeProject?.id]);

  const loadVersions = async () => {
    if (!activeProject?.id) return;
    setIsLoading(true);
    setActionSuccess(null);
    setActionError(null);
    try {
      const fetched = await projectService.fetchProjectVersions(activeProject.id);
      setVersions(fetched);
      setSelectedVersion(fetched.length > 0 ? fetched[0] : null);
    } catch (err) {
      setActionError('Failed to load version history from backend.');
      setVersions([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRestore = async (version: ProjectVersion) => {
    if (!activeProject?.id) return;
    setIsActing(true);
    setActionSuccess(null);
    setActionError(null);
    try {
      await projectService.restoreVersion(activeProject.id, version.id);
      if (version.parameters) {
        setParameters(version.parameters);
      }
      setActionSuccess(`Version v${version.version_number} restored successfully.`);
      // Reload history to show the new restoration entry
      await loadVersions();
    } catch (err: any) {
      setActionError(`Restore failed: ${err.message || 'Unknown error'}`);
    } finally {
      setIsActing(false);
    }
  };

  const handleDuplicate = async (version: ProjectVersion) => {
    if (!activeProject?.id) return;
    setIsActing(true);
    setActionSuccess(null);
    setActionError(null);
    try {
      const res = await projectService.duplicateVersion(activeProject.id, version.id);
      setActionSuccess(`Branch created from v${version.version_number}. New project ID: ${res.new_project_id}`);
    } catch (err: any) {
      setActionError(`Duplicate failed: ${err.message || 'Unknown error'}`);
    } finally {
      setIsActing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 font-sans select-none">
      <div className="bg-white border border-slate-200 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden text-slate-800">

        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">Project Version History</h2>
              <p className="text-xs text-slate-500">
                {activeProject?.name || 'No project selected'} · Non-destructive design iterations
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">

          {/* Left: Version Timeline */}
          <div className="w-1/2 border-r border-slate-200 overflow-y-auto p-4 space-y-2 bg-slate-50/50">
            <h3 className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-3">
              Design Iteration Stack
            </h3>

            {isLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-20 bg-slate-200/60 rounded-xl animate-pulse" />
                ))}
              </div>
            ) : versions.length === 0 ? (
              <div className="text-center py-10 text-xs text-slate-400">
                <History className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                {activeProject?.id
                  ? 'No versions recorded yet. Generate a CAD design to start the history.'
                  : 'Open a project to view its version history.'}
              </div>
            ) : (
              <div className="space-y-2">
                {versions.map((ver) => {
                  const isSelected = selectedVersion?.id === ver.id;
                  return (
                    <div
                      key={ver.id}
                      onClick={() => setSelectedVersion(ver)}
                      className={`p-3.5 rounded-xl border text-left cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-white border-indigo-500 shadow-sm ring-1 ring-indigo-500/20'
                          : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="px-2 py-0.5 rounded-md text-[11px] font-mono font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                          v{ver.version_number}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400 flex items-center space-x-1">
                          <Clock className="w-3 h-3" />
                          <span>{ver.created_at ? new Date(ver.created_at).toLocaleString() : '—'}</span>
                        </span>
                      </div>

                      <p className="text-xs font-semibold text-slate-800 line-clamp-2 mt-1">
                        {ver.prompt || 'No description recorded'}
                      </p>

                      <div className="mt-2 flex items-center justify-between text-[10px] font-mono text-slate-400">
                        <span>{Object.keys(ver.parameters || {}).length} params recorded</span>
                        {ver.validation_result?.is_valid && (
                          <span className="text-emerald-600 flex items-center space-x-1">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Valid</span>
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Right: Inspector & Actions */}
          <div className="w-1/2 p-6 flex flex-col justify-between overflow-y-auto bg-white">
            {selectedVersion ? (
              <div className="space-y-5 text-xs font-mono">

                <div className="border-b border-slate-100 pb-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-base font-bold text-slate-900">Version v{selectedVersion.version_number}</span>
                    <span className="text-slate-400 text-[10px]">
                      {selectedVersion.created_at ? new Date(selectedVersion.created_at).toLocaleString() : '—'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 font-sans leading-relaxed">
                    {selectedVersion.prompt || 'No prompt recorded'}
                  </p>
                </div>

                {/* Parameters Snapshot */}
                {Object.keys(selectedVersion.parameters || {}).length > 0 && (
                  <div>
                    <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">
                      Parameter Snapshot
                    </h4>
                    <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 space-y-1.5">
                      {Object.entries(selectedVersion.parameters || {}).map(([key, val]) => (
                        <div key={key} className="flex justify-between">
                          <span className="text-slate-500">{key}:</span>
                          <span className="font-bold text-slate-800">{String(val)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Generated Files */}
                {selectedVersion.generated_files?.length > 0 && (
                  <div>
                    <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">
                      CAD Output
                    </h4>
                    <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Layers className="w-4 h-4 text-indigo-600" />
                        <span className="font-bold text-slate-800 truncate max-w-[200px]">
                          {selectedVersion.generated_files[0].split(/[/\\]/).pop()}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-400">
                        {selectedVersion.generated_files[0].endsWith('.stl') ? 'STL' : 'DXF'}
                      </span>
                    </div>
                  </div>
                )}

                {/* Action Feedback */}
                {actionSuccess && (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-xl font-mono text-xs flex items-start space-x-2">
                    <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{actionSuccess}</span>
                  </div>
                )}
                {actionError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl font-mono text-xs flex items-start space-x-2">
                    <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{actionError}</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center text-slate-400 text-xs text-center">
                Select a version from the timeline to inspect its parameters and output files.
              </div>
            )}

            {/* Action Buttons */}
            {selectedVersion && (
              <div className="pt-4 border-t border-slate-100 grid grid-cols-2 gap-3 mt-4">
                <button
                  onClick={() => handleRestore(selectedVersion)}
                  disabled={isActing}
                  className="py-2.5 px-3 bg-indigo-600 hover:bg-indigo-700 text-white font-mono text-xs font-bold rounded-xl flex items-center justify-center space-x-2 shadow-sm transition-all disabled:opacity-50"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Restore Version</span>
                </button>

                <button
                  onClick={() => handleDuplicate(selectedVersion)}
                  disabled={isActing}
                  className="py-2.5 px-3 bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 font-mono text-xs font-bold rounded-xl flex items-center justify-center space-x-2 transition-all disabled:opacity-50"
                >
                  <Copy className="w-3.5 h-3.5 text-slate-600" />
                  <span>Duplicate Branch</span>
                </button>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};
