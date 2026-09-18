import { create } from 'zustand';

export type CADExportFormat = 'STL' | 'STEP' | 'DXF' | 'OBJ' | 'IGES' | 'SVG' | 'GCODE';

interface ExportState {
  isExporting: boolean;
  exportFormat: CADExportFormat;
  exportResolution: 'coarse' | 'medium' | 'fine' | 'ultra';
  exportPath: string | null;
  exportProgress: number;
  lastExportedFile: string | null;
  exportError: string | null;

  // Actions
  setIsExporting: (exporting: boolean) => void;
  setExportFormat: (format: CADExportFormat) => void;
  setExportResolution: (res: 'coarse' | 'medium' | 'fine' | 'ultra') => void;
  setExportPath: (path: string | null) => void;
  setExportProgress: (progress: number) => void;
  setExportSuccess: (outputFile: string) => void;
  setExportError: (error: string) => void;
  resetExport: () => void;
}

export const useExportStore = create<ExportState>((set) => ({
  isExporting: false,
  exportFormat: 'STL',
  exportResolution: 'fine',
  exportPath: null,
  exportProgress: 0,
  lastExportedFile: null,
  exportError: null,

  setIsExporting: (isExporting) => set({ isExporting, exportError: null }),
  setExportFormat: (exportFormat) => set({ exportFormat }),
  setExportResolution: (exportResolution) => set({ exportResolution }),
  setExportPath: (exportPath) => set({ exportPath }),
  setExportProgress: (exportProgress) => set({ exportProgress }),
  setExportSuccess: (lastExportedFile) => set({
    isExporting: false,
    exportProgress: 100,
    lastExportedFile,
    exportError: null
  }),
  setExportError: (exportError) => set({
    isExporting: false,
    exportProgress: 0,
    exportError
  }),
  resetExport: () => set({
    isExporting: false,
    exportProgress: 0,
    lastExportedFile: null,
    exportError: null
  })
}));
