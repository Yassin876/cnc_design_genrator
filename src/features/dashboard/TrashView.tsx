import React, { useState, useEffect } from 'react';
import { Search, Hexagon, ArrowUpRight, Trash2, RefreshCw, AlertCircle, RotateCcw } from 'lucide-react';
import { projectsApiService, Project } from '../../services/api/projects';
import { DeleteConfirmModal } from '../../components/common/DeleteConfirmModal';

const TrashView: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [items, setItems] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [itemToDelete, setItemToDelete] = useState<Project | null>(null);
  const [isClearingAll, setIsClearingAll] = useState<boolean>(false);

  const fetchTrash = async () => {
    setIsLoading(true);
    try {
      const data = await projectsApiService.getTrashProjects();
      setItems(data);
    } catch (err) {
      console.error('Failed to fetch trash projects', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTrash();
  }, []);

  const handleRestore = async (id: string) => {
    // Optimistic UI update
    setItems((prev) => prev.filter((item) => item.id !== id));
    try {
      await projectsApiService.restoreFromTrash(id);
    } catch (err) {
      console.error('Failed to restore project', err);
      fetchTrash();
    }
  };

  const handleConfirmDelete = async () => {
    if (!itemToDelete) return;
    const id = itemToDelete.id;
    setItemToDelete(null);
    setItems((prev) => prev.filter((item) => item.id !== id));
    try {
      await projectsApiService.deletePermanently(id);
    } catch (err) {
      console.error('Failed to permanently delete project', err);
      fetchTrash();
    }
  };

  const handleConfirmClearAll = async () => {
    setIsClearingAll(false);
    setItems([]);
    try {
      await projectsApiService.clearTrash();
    } catch (err) {
      console.error('Failed to clear trash', err);
      fetchTrash();
    }
  };

  const filtered = items.filter((item) =>
    item.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex-1 bg-[#F8FAFC] text-slate-900 overflow-y-auto p-6 lg:p-10 font-sans select-none space-y-6 lg:space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl lg:text-3xl font-black tracking-tight text-slate-900">Trash</h1>
          <p className="text-xs text-slate-500 font-medium">Restore a project or permanently delete it along with its physical files.</p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="relative flex items-center flex-1 sm:flex-initial">
            <Search className="w-4 h-4 text-slate-400 absolute left-3" />
            <input
              type="text"
              placeholder="Search trash..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 outline-none w-full sm:w-64 shadow-xs focus:ring-2 focus:ring-indigo-600/30 focus:border-indigo-600 transition-all"
            />
          </div>

          {items.length > 0 && (
            <button
              onClick={() => setIsClearingAll(true)}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold shadow-md shadow-rose-600/20 flex items-center space-x-1.5 transition-all"
            >
              <Trash2 className="w-4 h-4" />
              <span>Empty Trash</span>
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-slate-900">Trash Items ({items.length})</h2>
        <button
          onClick={fetchTrash}
          className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg bg-white border border-slate-200"
          title="Refresh"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Trash List */}
      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-slate-200/60 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="p-16 text-center text-slate-400 bg-white border border-slate-200/90 rounded-2xl text-xs space-y-2">
          <Trash2 className="w-10 h-10 text-slate-300 mx-auto" />
          <h3 className="text-sm font-bold text-slate-700">Trash is empty</h3>
          <p className="text-xs text-slate-400">Deleted projects will be stored here for recovery.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((item) => (
            <div
              key={item.id}
              className="bg-white border border-slate-200/90 rounded-2xl p-4 flex items-center justify-between shadow-xs hover:shadow-sm transition-all"
            >
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-400">
                  {item.type === '3D' ? <Hexagon className="w-5 h-5" /> : <ArrowUpRight className="w-5 h-5" />}
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-900">{item.name}</h4>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    {item.type} Project · Version v{item.current_version}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2 text-xs font-semibold">
                <button
                  onClick={() => handleRestore(item.id)}
                  className="flex items-center space-x-1 px-3 py-1.5 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 rounded-xl transition-all"
                  title="Restore project"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
                  <span>Restore</span>
                </button>
                <button
                  onClick={() => setItemToDelete(item)}
                  className="flex items-center space-x-1 px-3 py-1.5 text-rose-600 hover:text-rose-700 hover:bg-rose-50 border border-transparent hover:border-rose-200 rounded-xl transition-all"
                  title="Permanently Delete"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Delete Permanently</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete Single Item Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={Boolean(itemToDelete)}
        title="Permanently Delete Project?"
        message={`Are you sure you want to permanently delete "${itemToDelete?.name}"? This action cannot be undone and will permanently remove all associated 3D/2D files from disk.`}
        confirmText="Permanently Delete"
        cancelText="Cancel"
        onConfirm={handleConfirmDelete}
        onCancel={() => setItemToDelete(null)}
      />

      {/* Clear All Trash Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={isClearingAll}
        title="Empty Entire Trash?"
        message="Are you sure you want to permanently delete all items in Trash? All associated CAD files will be permanently erased."
        confirmText="Empty Trash"
        cancelText="Cancel"
        onConfirm={handleConfirmClearAll}
        onCancel={() => setIsClearingAll(false)}
      />
    </div>
  );
};

export default TrashView;
