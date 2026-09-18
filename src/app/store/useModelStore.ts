import { create } from 'zustand';
import { MeshInspection, ModelTransform } from '../../types';

interface ModelState {
  activeFilePath: string | null;
  activeFileName: string | null;
  designType: '2D' | '3D';
  format: string;
  material: string;
  units: 'mm' | 'cm' | 'm' | 'inch';
  
  // Transform & Geometry Metadata
  transform: ModelTransform;
  dimensions: { width: number; height: number; depth: number };
  parameters: Record<string, any>;
  inspectionData: MeshInspection | null;
  dxfEntities: any[] | null;

  // Actions
  setModelFile: (filePath: string, designType: '2D' | '3D', format?: string) => void;
  setMaterial: (material: string) => void;
  setUnits: (units: 'mm' | 'cm' | 'm' | 'inch') => void;
  setTransform: (transform: Partial<ModelTransform>) => void;
  setParameter: (key: string, value: any) => void;
  setParameters: (params: Record<string, any>) => void;
  setInspectionData: (data: MeshInspection | null) => void;
  setDxfEntities: (entities: any[] | null) => void;
  resetModel: () => void;
}

export const useModelStore = create<ModelState>((set) => ({
  activeFilePath: null,
  activeFileName: null,
  designType: '3D',
  format: 'STL',
  material: 'Industrial Steel 304',
  units: 'mm',

  transform: {
    position: { x: 0, y: 0, z: 0 },
    rotation: { x: 0, y: 0, z: 0 },
    scale: { x: 1, y: 1, z: 1 }
  },
  dimensions: { width: 100, height: 100, depth: 50 },
  parameters: {
    inner_diameter: 50,
    wall_thickness: 5,
    bend_angle: 90,
    flange_outer_diameter: 110,
    mounting_holes: 4,
    hole_diameter: 8
  },
  inspectionData: null,
  dxfEntities: null,

  setModelFile: (activeFilePath, designType, format = 'STL') => set({
    activeFilePath,
    activeFileName: activeFilePath.split(/[/\\]/).pop() || 'Untitled Model',
    designType,
    format
  }),
  setMaterial: (material) => set({ material }),
  setUnits: (units) => set({ units }),
  setTransform: (t) => set((s) => ({
    transform: {
      position: { ...s.transform.position, ...t.position },
      rotation: { ...s.transform.rotation, ...t.rotation },
      scale: { ...s.transform.scale, ...t.scale }
    }
  })),
  setParameter: (key, value) => set((s) => ({
    parameters: { ...s.parameters, [key]: value }
  })),
  setParameters: (parameters) => set({ parameters }),
  setInspectionData: (inspectionData) => set({ inspectionData }),
  setDxfEntities: (dxfEntities) => set({ dxfEntities }),
  resetModel: () => set({
    activeFilePath: null,
    activeFileName: null,
    inspectionData: null,
    dxfEntities: null
  })
}));
