import React, { useState, useEffect } from 'react';
import { X, Layers3, Play, CheckCircle2, Plus, Trash2, ArrowUp, ArrowDown, Zap, RotateCw, Settings2 } from 'lucide-react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { use2DWorkspaceStore } from '../../app/store/use2DWorkspaceStore';
import { cadService } from '../../services/cad/cadService';
import { NestResult } from '../../types';

interface Part {
  id: string;
  name: string;
  path?: string;
  qty: number;
  thickness: number;
  priority: 'High' | 'Normal' | 'Low';
  priorityOrder: number;
  selected: boolean;
}

interface StockSheet {
  id: string;
  material: string;
  width: number;
  height: number;
  thickness: number;
  availableQty: number;
  unlimited: boolean;
}

export const NestingDialog: React.FC = () => {
  const { isNestingModalOpen, setNestingModalOpen, dxfContent, activeFilePath, activeFileName, loadFile } = useWorkspaceStore();
  const store2D = use2DWorkspaceStore();
  const workspacePath = store2D.activeFilePath || activeFilePath;
  const workspaceName = store2D.activeFileName || activeFileName;

  // Tab state
  const [activeTab, setActiveTab] = useState<'parts' | 'stock' | 'settings'>('parts');

  // Parts state
  const [parts, setParts] = useState<Part[]>([]);
  const [selectedPartIndex, setSelectedPartIndex] = useState<number | null>(null);

  // Stock sheets state
  const [stockSheets, setStockSheets] = useState<StockSheet[]>([
    { id: '1', material: 'Steel', width: 1200, height: 600, thickness: 18, availableQty: 10, unlimited: false }
  ]);
  const [selectedStockIndex, setSelectedStockIndex] = useState<number | null>(null);

  // Settings state
  const [spacing, setSpacing] = useState<number>(5.0);
  const [allowRotate, setAllowRotate] = useState<boolean>(true);
  const [nestingMode, setNestingMode] = useState<'priority' | 'optimize'>('priority');
  const [continueIncomplete, setContinueIncomplete] = useState<boolean>(true);

  // Nesting state
  const [isNesting, setIsNesting] = useState<boolean>(false);
  const [nestResult, setNestResult] = useState<NestResult | null>(null);
  const [nestError, setNestError] = useState<string | null>(null);

  // Initialize parts from workspace
  useEffect(() => {
    if (isNestingModalOpen) {
      // Create part from current DXF in workspace
      // Note: For external API flow (dxfContent without path), nesting may not work until backend supports in-memory DXF
      const newPart: Part = {
        id: Date.now().toString(),
        name: workspaceName || (dxfContent ? 'Generated Part (in-memory)' : 'Current Part'),
        path: workspacePath || undefined,
        qty: 1,
        thickness: stockSheets[0]?.thickness ?? 18.0,
        priority: 'Normal',
        priorityOrder: 100,
        selected: true
      };
      setParts([newPart]);
      setSelectedPartIndex(null);
      setNestResult(null);
      setNestError(null);
    }
  }, [isNestingModalOpen, workspaceName, workspacePath, dxfContent]);

  const handleSetHighPriority = () => {
    if (selectedPartIndex !== null) {
      const updated = [...parts];
      updated[selectedPartIndex].priority = 'High';
      updated[selectedPartIndex].priorityOrder = 10;
      setParts(updated);
    }
  };

  const handleMoveUp = () => {
    if (selectedPartIndex !== null && selectedPartIndex > 0) {
      const updated = [...parts];
      const temp = updated[selectedPartIndex];
      updated[selectedPartIndex] = updated[selectedPartIndex - 1];
      updated[selectedPartIndex - 1] = temp;
      setParts(updated);
      setSelectedPartIndex(selectedPartIndex - 1);
    }
  };

  const handleMoveDown = () => {
    if (selectedPartIndex !== null && selectedPartIndex < parts.length - 1) {
      const updated = [...parts];
      const temp = updated[selectedPartIndex];
      updated[selectedPartIndex] = updated[selectedPartIndex + 1];
      updated[selectedPartIndex + 1] = temp;
      setParts(updated);
      setSelectedPartIndex(selectedPartIndex + 1);
    }
  };

  const handleAddStockSheet = () => {
    const newSheet: StockSheet = {
      id: Date.now().toString(),
      material: 'Steel',
      width: 1200,
      height: 600,
      thickness: 18,
      availableQty: 10,
      unlimited: false
    };
    setStockSheets([...stockSheets, newSheet]);
  };

  const handleDeleteStockSheet = () => {
    if (selectedStockIndex !== null) {
      const updated = stockSheets.filter((_, i) => i !== selectedStockIndex);
      setStockSheets(updated);
      setSelectedStockIndex(null);
    }
  };

  const handleRunNesting = async () => {
    setIsNesting(true);
    setNestError(null);
    setNestResult(null);

    try {
      // Get selected parts with paths or in-memory dxf content
      const selectedParts = parts.filter(p => p.selected);
      if (selectedParts.length === 0) {
        throw new Error('No parts selected for nesting. Please select at least one part.');
      }

      // Check if parts have paths or in-memory dxf content
      const unnestable = selectedParts.filter(p => !p.path && !dxfContent);
      if (unnestable.length > 0) {
        throw new Error('No geometry found for one or more parts. Please load or generate a DXF first.');
      }

      // Get stock sheets
      const sheetParams = stockSheets.map(s => ({
        width: s.width,
        height: s.height,
        thickness: s.thickness,
        quantity: s.unlimited ? 9999 : s.availableQty
      }));

      // For now, use the first sheet (simplified)
      const firstSheet = sheetParams[0] || { width: 1200, height: 600, thickness: 18, quantity: 10 };

      const partPayloads = selectedParts.map(p => ({
        path: p.path || '',
        dxf_content: !p.path ? (dxfContent || undefined) : undefined,
        name: p.name,
        quantity: p.qty,
        thickness: p.thickness,
        priority: p.priority,
        priority_order: p.priorityOrder
      }));

      const res = await cadService.runNesting(
        partPayloads,
        firstSheet.width,
        firstSheet.height,
        spacing,
        allowRotate,
        firstSheet.thickness
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

  if (!isNestingModalOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-md flex items-center justify-center p-4 select-none font-sans">
      <div className="bg-white border border-slate-200 w-full max-w-4xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-white">
          <div className="flex items-center space-x-2 font-bold text-sm text-slate-900">
            <Layers3 className="w-5 h-5 text-amber-600" />
            <span>Nest Parts Configuration</span>
          </div>
          <button
            onClick={() => setNestingModalOpen(false)}
            className="text-slate-400 hover:text-slate-700 p-1 rounded-lg hover:bg-slate-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-200 bg-slate-50">
          {[
            { id: 'parts' as const, label: '1. Parts Priorities' },
            { id: 'stock' as const, label: '2. Stock Sheet Inventory' },
            { id: 'settings' as const, label: '3. Nesting Mode Settings' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-xs font-mono font-bold border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-700 bg-white'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          
          {/* Tab 1: Parts Priorities */}
          {activeTab === 'parts' && (
            <div className="space-y-4">
              {/* Action buttons */}
              <div className="flex gap-2">
                <button
                  onClick={handleSetHighPriority}
                  disabled={selectedPartIndex === null}
                  className="px-3 py-2 bg-amber-500 hover:bg-amber-600 text-black text-xs font-bold rounded-lg flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Zap className="w-3.5 h-3.5" />
                  <span>Set as High Priority</span>
                </button>
                <button
                  onClick={handleMoveUp}
                  disabled={selectedPartIndex === null}
                  className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-lg flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ArrowUp className="w-3.5 h-3.5" />
                  <span>Move Up</span>
                </button>
                <button
                  onClick={handleMoveDown}
                  disabled={selectedPartIndex === null}
                  className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-lg flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ArrowDown className="w-3.5 h-3.5" />
                  <span>Move Down</span>
                </button>
              </div>

              {/* Parts table */}
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-xs font-mono">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">Nest</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">DXF Part File</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">Qty</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">Thickness (mm)</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">Priority</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">Priority Order</th>
                    </tr>
                  </thead>
                  <tbody>
                    {parts.map((part, index) => (
                      <tr
                        key={part.id}
                        onClick={() => setSelectedPartIndex(index)}
                        className={`border-b border-slate-100 cursor-pointer hover:bg-slate-50 ${
                          selectedPartIndex === index ? 'bg-indigo-50' : ''
                        }`}
                      >
                        <td className="px-3 py-2">
                          <input
                            type="checkbox"
                            checked={part.selected}
                            onChange={(e) => {
                              const updated = [...parts];
                              updated[index].selected = e.target.checked;
                              setParts(updated);
                            }}
                            onClick={(e) => e.stopPropagation()}
                            className="accent-indigo-600 w-4 h-4"
                          />
                        </td>
                        <td className="px-3 py-2">
                          <div className="flex items-center space-x-2">
                            <span className="text-slate-900">{part.name}</span>
                            {!part.path && (
                              <span className="text-[10px] text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">In-memory</span>
                            )}
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          <input
                            type="number"
                            min="1"
                            max="9999"
                            value={part.qty}
                            onChange={(e) => {
                              const updated = [...parts];
                              updated[index].qty = parseInt(e.target.value) || 1;
                              setParts(updated);
                            }}
                            onClick={(e) => e.stopPropagation()}
                            className="w-16 px-2 py-1 border border-slate-200 rounded text-center"
                          />
                        </td>
                        <td className="px-3 py-2">
                          <input
                            type="number"
                            min="0.1"
                            max="1000"
                            step="0.1"
                            value={part.thickness}
                            onChange={(e) => {
                              const updated = [...parts];
                              updated[index].thickness = parseFloat(e.target.value) || 18;
                              setParts(updated);
                            }}
                            onClick={(e) => e.stopPropagation()}
                            className="w-20 px-2 py-1 border border-slate-200 rounded text-center"
                          />
                        </td>
                        <td className="px-3 py-2">
                          <select
                            value={part.priority}
                            onChange={(e) => {
                              const updated = [...parts];
                              updated[index].priority = e.target.value as 'High' | 'Normal' | 'Low';
                              updated[index].priorityOrder = e.target.value === 'High' ? 10 : e.target.value === 'Normal' ? 100 : 200;
                              setParts(updated);
                            }}
                            onClick={(e) => e.stopPropagation()}
                            className="px-2 py-1 border border-slate-200 rounded bg-white"
                          >
                            <option value="High">High</option>
                            <option value="Normal">Normal</option>
                            <option value="Low">Low</option>
                          </select>
                        </td>
                        <td className="px-3 py-2">
                          <input
                            type="number"
                            min="1"
                            max="9999"
                            value={part.priorityOrder}
                            onChange={(e) => {
                              const updated = [...parts];
                              updated[index].priorityOrder = parseInt(e.target.value) || 100;
                              setParts(updated);
                            }}
                            onClick={(e) => e.stopPropagation()}
                            className="w-20 px-2 py-1 border border-slate-200 rounded text-center"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tab 2: Stock Sheet Inventory */}
          {activeTab === 'stock' && (
            <div className="space-y-4">
              {/* Action buttons */}
              <div className="flex gap-2">
                <button
                  onClick={handleAddStockSheet}
                  className="px-3 py-2 bg-emerald-500 hover:bg-emerald-600 text-black text-xs font-bold rounded-lg flex items-center space-x-1.5"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Stock Sheet</span>
                </button>
                <button
                  onClick={handleDeleteStockSheet}
                  disabled={selectedStockIndex === null}
                  className="px-3 py-2 bg-red-500 hover:bg-red-600 text-white text-xs font-bold rounded-lg flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Delete Selected Sheet</span>
                </button>
              </div>

              {/* Stock sheets table */}
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-xs font-mono">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">Material Name</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">Width (mm)</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">Height (mm)</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">Thickness (mm)</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">Available Qty</th>
                      <th className="px-3 py-2 text-left font-bold text-slate-700">Unlimited</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stockSheets.map((sheet, index) => (
                      <tr
                        key={sheet.id}
                        onClick={() => setSelectedStockIndex(index)}
                        className={`border-b border-slate-100 cursor-pointer hover:bg-slate-50 ${
                          selectedStockIndex === index ? 'bg-indigo-50' : ''
                        }`}
                      >
                        <td className="px-3 py-2">
                          <input
                            type="text"
                            value={sheet.material}
                            onChange={(e) => {
                              const updated = [...stockSheets];
                              updated[index].material = e.target.value;
                              setStockSheets(updated);
                            }}
                            onClick={(e) => e.stopPropagation()}
                            className="w-full px-2 py-1 border border-slate-200 rounded"
                          />
                        </td>
                        <td className="px-3 py-2">
                          <input
                            type="number"
                            value={sheet.width}
                            onChange={(e) => {
                              const updated = [...stockSheets];
                              updated[index].width = parseFloat(e.target.value) || 1200;
                              setStockSheets(updated);
                            }}
                            onClick={(e) => e.stopPropagation()}
                            className="w-20 px-2 py-1 border border-slate-200 rounded text-center"
                          />
                        </td>
                        <td className="px-3 py-2">
                          <input
                            type="number"
                            value={sheet.height}
                            onChange={(e) => {
                              const updated = [...stockSheets];
                              updated[index].height = parseFloat(e.target.value) || 600;
                              setStockSheets(updated);
                            }}
                            onClick={(e) => e.stopPropagation()}
                            className="w-20 px-2 py-1 border border-slate-200 rounded text-center"
                          />
                        </td>
                        <td className="px-3 py-2">
                          <input
                            type="number"
                            value={sheet.thickness}
                            onChange={(e) => {
                              const updated = [...stockSheets];
                              updated[index].thickness = parseFloat(e.target.value) || 18;
                              setStockSheets(updated);
                            }}
                            onClick={(e) => e.stopPropagation()}
                            className="w-20 px-2 py-1 border border-slate-200 rounded text-center"
                          />
                        </td>
                        <td className="px-3 py-2">
                          <input
                            type="number"
                            min="0"
                            value={sheet.availableQty}
                            onChange={(e) => {
                              const updated = [...stockSheets];
                              updated[index].availableQty = parseInt(e.target.value) || 0;
                              setStockSheets(updated);
                            }}
                            onClick={(e) => e.stopPropagation()}
                            className="w-20 px-2 py-1 border border-slate-200 rounded text-center"
                          />
                        </td>
                        <td className="px-3 py-2">
                          <input
                            type="checkbox"
                            checked={sheet.unlimited}
                            onChange={(e) => {
                              const updated = [...stockSheets];
                              updated[index].unlimited = e.target.checked;
                              setStockSheets(updated);
                            }}
                            onClick={(e) => e.stopPropagation()}
                            className="accent-indigo-600 w-4 h-4"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tab 3: Nesting Mode Settings */}
          {activeTab === 'settings' && (
            <div className="space-y-6">
              {/* Global Nesting Parameters */}
              <div className="border border-slate-200 rounded-xl p-4">
                <div className="flex items-center space-x-2 font-bold text-sm text-slate-900 mb-4">
                  <Settings2 className="w-4 h-4 text-indigo-600" />
                  <span>Global Nesting Parameters</span>
                </div>

                <div className="space-y-4 font-mono text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-600">Spacing between parts (mm):</span>
                    <input
                      type="number"
                      min="0"
                      max="500"
                      step="0.1"
                      value={spacing}
                      onChange={(e) => setSpacing(parseFloat(e.target.value) || 5)}
                      className="w-24 px-2 py-1 border border-slate-200 rounded text-center"
                    />
                  </div>

                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={allowRotate}
                      onChange={(e) => setAllowRotate(e.target.checked)}
                      className="accent-indigo-600 w-4 h-4"
                    />
                    <span className="text-slate-700">Allow 90° Part Rotation</span>
                  </label>
                </div>
              </div>

              {/* Nesting Strategy Mode */}
              <div className="border border-slate-200 rounded-xl p-4">
                <div className="flex items-center space-x-2 font-bold text-sm text-slate-900 mb-4">
                  <RotateCw className="w-4 h-4 text-cyan-600" />
                  <span>Nesting Strategy Mode</span>
                </div>

                <div className="space-y-3 font-mono text-xs">
                  <label className="flex items-start space-x-2 cursor-pointer">
                    <input
                      type="radio"
                      name="nestingMode"
                      checked={nestingMode === 'priority'}
                      onChange={() => setNestingMode('priority')}
                      className="accent-indigo-600 w-4 h-4 mt-0.5"
                    />
                    <span className="text-slate-700">
                      <span className="font-bold text-emerald-600">Finish priority parts first</span>
                      <span className="text-slate-500 block mt-1">Complete urgent parts on earliest production sheets</span>
                    </span>
                  </label>

                  <label className="flex items-start space-x-2 cursor-pointer">
                    <input
                      type="radio"
                      name="nestingMode"
                      checked={nestingMode === 'optimize'}
                      onChange={() => setNestingMode('optimize')}
                      className="accent-indigo-600 w-4 h-4 mt-0.5"
                    />
                    <span className="text-slate-700">
                      <span className="font-bold text-slate-900">Optimize material usage</span>
                      <span className="text-slate-500 block mt-1">Maximize overall material utilization efficiency</span>
                    </span>
                  </label>

                  <label className="flex items-start space-x-2 cursor-pointer pt-2">
                    <input
                      type="checkbox"
                      checked={continueIncomplete}
                      onChange={(e) => setContinueIncomplete(e.target.checked)}
                      className="accent-indigo-600 w-4 h-4 mt-0.5"
                    />
                    <span className="text-slate-700">Continue nesting lower-priority parts when a priority group is incomplete</span>
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* Nesting Results */}
          {nestResult && (
            <div className="mt-6 bg-emerald-50 border border-emerald-200 rounded-xl p-4 space-y-4">
              <div className="flex items-center space-x-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                <span className="font-bold text-emerald-800 text-sm">Nesting complete!</span>
              </div>
              <p className="text-xs font-mono text-emerald-700">
                Placed {nestResult.total_parts_placed} part(s) on {nestResult.total_sheets_used} stock sheet(s). Material efficiency: {nestResult.total_utilization.toFixed(1)}%
              </p>
              <div className="grid grid-cols-4 gap-2 text-center font-mono text-xs">
                <div className="bg-white p-2 rounded border border-emerald-200">
                  <span className="text-emerald-600 block">Parts Placed</span>
                  <span className="font-bold text-emerald-800">{nestResult.total_parts_placed} / {nestResult.total_parts_required}</span>
                </div>
                <div className="bg-white p-2 rounded border border-emerald-200">
                  <span className="text-emerald-600 block">Sheets Used</span>
                  <span className="font-bold text-emerald-800">{nestResult.total_sheets_used}</span>
                </div>
                <div className="bg-white p-2 rounded border border-emerald-200">
                  <span className="text-emerald-600 block">Utilization</span>
                  <span className="font-bold text-emerald-800">{nestResult.total_utilization.toFixed(1)}%</span>
                </div>
                <div className="bg-white p-2 rounded border border-emerald-200">
                  <span className="text-emerald-600 block">Waste</span>
                  <span className="font-bold text-emerald-800">{nestResult.total_waste.toFixed(1)}%</span>
                </div>
              </div>
            </div>
          )}

          {nestError && (
            <div className="mt-6 bg-red-50 border border-red-200 rounded-xl p-4 text-xs font-mono text-red-800">
              {nestError}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-white flex items-center justify-end space-x-3">
          <button
            onClick={() => setNestingModalOpen(false)}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl"
          >
            Cancel
          </button>

          <button
            onClick={handleRunNesting}
            disabled={isNesting}
            className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-md shadow-indigo-600/20 flex items-center space-x-2 transition-all disabled:opacity-50"
          >
            {isNesting ? (
              <span>Calculating...</span>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white" />
                <span>Nest Parts</span>
              </>
            )}
          </button>
        </div>

      </div>
    </div>
  );
};
