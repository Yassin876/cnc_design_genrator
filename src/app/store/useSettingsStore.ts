import { create } from 'zustand';

export type SettingsTab = 
  | 'account'
  | 'general'
  | 'ai'
  | 'compute'
  | 'units'
  | 'cad'
  | 'export'
  | 'shortcuts'
  | 'storage'
  | 'about';

export type UnitType = 'mm' | 'cm' | 'm' | 'inch';

export interface AIModelStatus {
  id: string;
  name: string;
  provider: string;
  type: string;
  status: 'Online' | 'Ready' | 'Offline';
  latencyMs: number;
  gpuAccelerated: boolean;
}

export interface ShortcutItem {
  id: string;
  label: string;
  category: 'Viewport' | 'Tools' | 'AI' | 'File';
  keyCombination: string;
}

export interface SettingsState {
  activeTab: SettingsTab;
  
  // Account
  accountName: string;
  accountEmail: string;
  accountRole: string;
  licenseTier: string;

  // General
  autoSaveIntervalSec: number;
  startupView: 'dashboard' | 'workspace_3d' | 'workspace_2d';
  backendApiUrl: string;
  dxfApiUrl: string;
  stlApiUrl: string;
  telemetryEnabled: boolean;

  // Appearance - Strict Product Direction: Light Theme Primary
  theme: 'light';
  accentColor: 'indigo' | 'violet' | 'sky' | 'slate';
  uiDensity: 'dense' | 'standard';
  highContrastBorders: boolean;
  viewportBgTone: 'off-white' | 'cool-gray' | 'pure-white';

  // AI Models
  primaryModel: string;
  computeDevice: string;
  gpuAvailable: boolean;
  gpuDeviceName: string;
  vramUsageMB: number;
  availableModels: AIModelStatus[];

  // Compute / GPU
  threadsCount: number;
  webGpuEnabled: boolean;
  meshOptimizationAccel: boolean;
  maxMemoryAllocGB: number;

  // Units
  units: UnitType;
  unitPrecision: number;
  angularUnits: 'deg' | 'rad';

  // CAD Preferences
  gridEnabled: boolean;
  gridSize: number;
  gridSubdivisions: number;
  snapToGrid: boolean;
  snapToEndpoint: boolean;
  snapTolerancePx: number;
  selectionMode: 'window' | 'crossing';
  hoverHighlight: boolean;
  selectionOutline: boolean;
  cameraFov: number;
  shadowsEnabled: boolean;
  groundPlaneGrid: boolean;
  defaultMaterial: string;
  defaultExportFormat: 'STL' | 'STEP' | 'DXF' | 'OBJ' | 'IGES';

  // Export
  exportOutputDir: string;
  stlResolution: 'coarse' | 'medium' | 'fine' | 'ultra';
  stepTolerance: number;
  dxfPolylineTol: number;
  autoOpenFolderOnExport: boolean;

  // Shortcuts
  shortcuts: ShortcutItem[];

  // Storage
  maxProjectVersions: number;
  cacheSizeMB: number;
  lastCacheClean: string;

  // Actions
  setActiveTab: (tab: SettingsTab) => void;
  setUnits: (units: UnitType) => void;
  updateCadPreferences: (prefs: Partial<SettingsState>) => void;
  updateAiConfig: (config: Partial<SettingsState>) => void;
  updateExportSettings: (settings: Partial<SettingsState>) => void;
  updateApiUrls: (urls: { dxfApiUrl?: string; stlApiUrl?: string; backendApiUrl?: string }) => void;
  updateShortcut: (id: string, newKey: string) => void;
  clearCache: () => void;
  resetToDefaults: () => void;
}

const defaultShortcuts: ShortcutItem[] = [
  { id: 'sc_orbit', label: 'Orbit Viewport', category: 'Viewport', keyCombination: 'Right Click + Drag' },
  { id: 'sc_pan', label: 'Pan Viewport', category: 'Viewport', keyCombination: 'Middle Click + Drag' },
  { id: 'sc_zoom', label: 'Zoom Viewport', category: 'Viewport', keyCombination: 'Scroll Wheel' },
  { id: 'sc_wireframe', label: 'Toggle Wireframe Overlay', category: 'Viewport', keyCombination: 'Shift + W' },
  { id: 'sc_grid', label: 'Toggle Grid / Snap', category: 'Viewport', keyCombination: 'G' },
  { id: 'sc_ai_prompt', label: 'Focus AI Prompt Console', category: 'AI', keyCombination: 'Ctrl + K' },
  { id: 'sc_generate', label: 'Submit AI Generation', category: 'AI', keyCombination: 'Ctrl + Enter' },
  { id: 'sc_export', label: 'Quick Export', category: 'File', keyCombination: 'Ctrl + E' },
  { id: 'sc_undo', label: 'Undo Parameter Edit', category: 'Tools', keyCombination: 'Ctrl + Z' },
  { id: 'sc_redo', label: 'Redo Parameter Edit', category: 'Tools', keyCombination: 'Ctrl + Y' }
];

export const useSettingsStore = create<SettingsState>((set) => ({
  activeTab: 'cad',

  // Account
  accountName: 'CAD Engineer',
  accountEmail: 'engineer@antidesign.local',
  accountRole: 'Lead CNC Designer',
  licenseTier: 'Professional Desktop Suite',

  // General
  autoSaveIntervalSec: 60,
  startupView: 'workspace_3d',
  backendApiUrl: 'http://127.0.0.1:8000/api/v1',
  dxfApiUrl: (typeof localStorage !== 'undefined' && localStorage.getItem('ANTI_DESIGN_DXF_API_URL')) || 'http://127.0.0.1:8000/api/v1/generation',
  stlApiUrl: (typeof localStorage !== 'undefined' && localStorage.getItem('ANTI_DESIGN_STL_API_URL') && !localStorage.getItem('ANTI_DESIGN_STL_API_URL')?.includes('7067-41-41-119-63') && !localStorage.getItem('ANTI_DESIGN_STL_API_URL')?.includes('7f44-41-41-247-228') ? localStorage.getItem('ANTI_DESIGN_STL_API_URL')! : 'https://7375-41-41-144-187.ngrok-free.app'),
  telemetryEnabled: false,

  // Appearance - Light Theme Primary
  theme: 'light',
  accentColor: 'indigo',
  uiDensity: 'dense',
  highContrastBorders: true,
  viewportBgTone: 'off-white',

  // AI Models
  primaryModel: 'Google Gemini 2.0 Flash (CAD Native)',
  computeDevice: 'NVIDIA GeForce RTX (PyTorch CUDA 12.1)',
  gpuAvailable: true,
  gpuDeviceName: 'NVIDIA GeForce RTX 3080 / 4090',
  vramUsageMB: 4096,
  availableModels: [
    { id: 'm_gemini', name: 'Gemini 2.0 Flash', provider: 'Google AI', type: 'Text-to-CAD Parameter Engine', status: 'Online', latencyMs: 140, gpuAccelerated: true },
    { id: 'm_flux', name: 'Flux.1 Schnell', provider: 'Hugging Face', type: 'Reference Latent Diffusion', status: 'Online', latencyMs: 450, gpuAccelerated: true },
    { id: 'm_deepseek', name: 'DeepSeek CAD Code', provider: 'Local Engine', type: 'PyOpenCASCADE Synthesizer', status: 'Ready', latencyMs: 210, gpuAccelerated: true },
    { id: 'm_opencad', name: 'OpenCAD Mesh Net', provider: 'Native C++', type: 'Mesh Decimation & Repair', status: 'Ready', latencyMs: 35, gpuAccelerated: true }
  ],

  // Compute / GPU
  threadsCount: 8,
  webGpuEnabled: true,
  meshOptimizationAccel: true,
  maxMemoryAllocGB: 16,

  // Units
  units: 'mm',
  unitPrecision: 0.01,
  angularUnits: 'deg',

  // CAD Preferences
  gridEnabled: true,
  gridSize: 10,
  gridSubdivisions: 10,
  snapToGrid: true,
  snapToEndpoint: true,
  snapTolerancePx: 8,
  selectionMode: 'window',
  hoverHighlight: true,
  selectionOutline: true,
  cameraFov: 45,
  shadowsEnabled: true,
  groundPlaneGrid: true,
  defaultMaterial: 'Industrial Steel 304',
  defaultExportFormat: 'STL',

  // Export
  exportOutputDir: 'd:\\cnc_design_genrator\\outputs',
  stlResolution: 'fine',
  stepTolerance: 0.001,
  dxfPolylineTol: 0.01,
  autoOpenFolderOnExport: true,

  // Shortcuts
  shortcuts: defaultShortcuts,

  // Storage
  maxProjectVersions: 25,
  cacheSizeMB: 142.5,
  lastCacheClean: '2026-08-23 18:30',

  // Actions
  setActiveTab: (activeTab) => set({ activeTab }),
  setUnits: (units) => set({ units }),
  updateCadPreferences: (prefs) => set((s) => ({ ...s, ...prefs })),
  updateAiConfig: (config) => set((s) => ({ ...s, ...config })),
  updateExportSettings: (settings) => set((s) => ({ ...s, ...settings })),
  updateApiUrls: (urls) => set((s) => {
    if (urls.dxfApiUrl !== undefined && typeof localStorage !== 'undefined') {
      localStorage.setItem('ANTI_DESIGN_DXF_API_URL', urls.dxfApiUrl);
    }
    if (urls.stlApiUrl !== undefined && typeof localStorage !== 'undefined') {
      localStorage.setItem('ANTI_DESIGN_STL_API_URL', urls.stlApiUrl);
    }
    return { ...s, ...urls };
  }),
  updateShortcut: (id, newKey) => set((s) => ({
    shortcuts: s.shortcuts.map((sc) => sc.id === id ? { ...sc, keyCombination: newKey } : sc)
  })),
  clearCache: () => set({ cacheSizeMB: 0, lastCacheClean: new Date().toISOString().replace('T', ' ').slice(0, 16) }),
  resetToDefaults: () => set((s) => ({
    units: 'mm',
    gridEnabled: true,
    gridSize: 10,
    snapToGrid: true,
    defaultMaterial: 'Industrial Steel 304',
    defaultExportFormat: 'STL',
    stlResolution: 'fine'
  }))
}));
