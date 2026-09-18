import { create } from 'zustand';
import { ChatMessage, FileAttachment, JobStageState } from '../../types';
import { apiClient } from '../../services/api/client';

// Helper: Calculate bounding box of entities
function calculateBoundingBox(entities: any[] | null): { minX: number; minY: number; maxX: number; maxY: number; width: number; height: number } | null {
  if (!entities || entities.length === 0) return null;
  
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  
  for (const entity of entities) {
    // Check points array (LINE, LWPOLYLINE, etc.)
    if (entity.points && entity.points.length > 0) {
      for (const point of entity.points) {
        const x = point[0];
        const y = point[1];
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
    
    // Check center (CIRCLE, ARC)
    if (entity.center) {
      const cx = entity.center[0];
      const cy = entity.center[1];
      const radius = entity.radius || 0;
      if (cx - radius < minX) minX = cx - radius;
      if (cx + radius > maxX) maxX = cx + radius;
      if (cy - radius < minY) minY = cy - radius;
      if (cy + radius > maxY) maxY = cy + radius;
    }
    
    // Check start/end (LINE)
    if (entity.start) {
      const x = entity.start[0];
      const y = entity.start[1];
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
    if (entity.end) {
      const x = entity.end[0];
      const y = entity.end[1];
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
    
    // Check dimension points
    if (entity.p1) {
      const x = entity.p1[0];
      const y = entity.p1[1];
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
    if (entity.p2) {
      const x = entity.p2[0];
      const y = entity.p2[1];
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
  }
  
  if (minX === Infinity) return null;
  
  return {
    minX,
    minY,
    maxX,
    maxY,
    width: maxX - minX,
    height: maxY - minY
  };
}

// Helper: Scale entities to new dimensions
function scaleEntitiesToDimensions(
  entities: any[] | null,
  newWidth: number,
  newHeight: number
): any[] | null {
  if (!entities || entities.length === 0) return null;
  
  const bbox = calculateBoundingBox(entities);
  if (!bbox || bbox.width === 0 || bbox.height === 0) return entities;
  
  const scaleX = newWidth / bbox.width;
  const scaleY = newHeight / bbox.height;
  const centerX = bbox.minX + bbox.width / 2;
  const centerY = bbox.minY + bbox.height / 2;
  
  // Scale each entity
  return entities.map(entity => {
    const scaledEntity = { ...entity };
    
    // Scale points array
    if (scaledEntity.points && scaledEntity.points.length > 0) {
      scaledEntity.points = scaledEntity.points.map((point: number[]) => {
        const x = point[0];
        const y = point[1];
        // Scale relative to center
        const newX = centerX + (x - centerX) * scaleX;
        const newY = centerY + (y - centerY) * scaleY;
        return [newX, newY];
      });
    }
    
    // Scale center (CIRCLE, ARC)
    if (scaledEntity.center) {
      const cx = scaledEntity.center[0];
      const cy = scaledEntity.center[1];
      scaledEntity.center = [
        centerX + (cx - centerX) * scaleX,
        centerY + (cy - centerY) * scaleY
      ];
      // Scale radius
      if (scaledEntity.radius) {
        scaledEntity.radius = scaledEntity.radius * Math.max(scaleX, scaleY);
      }
      if (scaledEntity.diameter) {
        scaledEntity.diameter = scaledEntity.diameter * Math.max(scaleX, scaleY);
      }
    }
    
    // Scale start/end (LINE)
    if (scaledEntity.start) {
      const x = scaledEntity.start[0];
      const y = scaledEntity.start[1];
      scaledEntity.start = [
        centerX + (x - centerX) * scaleX,
        centerY + (y - centerY) * scaleY
      ];
    }
    if (scaledEntity.end) {
      const x = scaledEntity.end[0];
      const y = scaledEntity.end[1];
      scaledEntity.end = [
        centerX + (x - centerX) * scaleX,
        centerY + (y - centerY) * scaleY
      ];
    }
    
    // Scale dimension points
    if (scaledEntity.p1) {
      const x = scaledEntity.p1[0];
      const y = scaledEntity.p1[1];
      scaledEntity.p1 = [
        centerX + (x - centerX) * scaleX,
        centerY + (y - centerY) * scaleY
      ];
    }
    if (scaledEntity.p2) {
      const x = scaledEntity.p2[0];
      const y = scaledEntity.p2[1];
      scaledEntity.p2 = [
        centerX + (x - centerX) * scaleX,
        centerY + (y - centerY) * scaleY
      ];
    }
    
    // Update bbox if present
    if (scaledEntity.bbox) {
      scaledEntity.bbox = {
        ...scaledEntity.bbox,
        w: scaledEntity.bbox.w * scaleX,
        h: scaledEntity.bbox.h * scaleY,
        cx: centerX + (scaledEntity.bbox.cx - centerX) * scaleX,
        cy: centerY + (scaledEntity.bbox.cy - centerY) * scaleY
      };
    }
    
    return scaledEntity;
  });
}

export interface Workspace2DState {
  // File & Project
  activeFilePath: string | null;
  activeFileName: string | null;
  isDirty: boolean;

  // DXF Data
  dxfEntities: any[] | null;

  // Undo History
  history: any[][];
  historyIndex: number;

  // 2D Parameters (editable, required before generate)
  width: number;
  height: number;
  toolDiameter: number;

  // View
  activeView: 'Front' | 'Top' | 'Right';

  // Generation state
  isGenerating: boolean;
  currentJobId: string | null;
  generatingStage: string;
  generatingProgress: number;
  generatingMessage: string;

  // Chat (no persistence)
  chatMessages: ChatMessage[];
  attachments: FileAttachment[];

  // Validation errors
  inputErrors: Record<string, string>;

  // Debounce timers for entity scaling
  widthDebounceTimer: NodeJS.Timeout | null;
  heightDebounceTimer: NodeJS.Timeout | null;

  // Actions
  setActiveFile: (filePath: string | null) => void;
  setDxfEntities: (entities: any[] | null) => void;
  undo: () => void;
  canUndo: () => boolean;
  redo: () => void;
  canRedo: () => boolean;
  setWidth: (val: number) => void;
  setHeight: (val: number) => void;
  setToolDiameter: (val: number) => void;
  setActiveView: (view: 'Front' | 'Top' | 'Right') => void;
  setGenerating: (isGenerating: boolean, stage?: string, progress?: number, message?: string, jobId?: string | null) => void;
  addChatMessage: (msg: ChatMessage) => void;
  setChatMessages: (msgs: ChatMessage[]) => void;
  addAttachment: (att: FileAttachment) => void;
  removeAttachment: (id: string) => void;
  clearAttachments: () => void;
  validateInputs: () => boolean;
  markDirty: () => void;
  saveWorkspace: () => Promise<boolean>;
  resetWorkspace: () => void;
}

const DEFAULT_WELCOME_MSG: ChatMessage = {
  id: 'welcome_2d',
  sender: 'ai',
  text: `👋 Welcome! I am **Anti Design** — your intelligent AI engineering & manufacturing CAD assistant.

I can assist you with the following:
1️⃣ **Generate 2D DXF Blueprints**: Describe your part and I'll generate a production-ready DXF file.
2️⃣ **Image to DXF Vectorization**: Upload a sketch or blueprint image to extract vector geometry & dimensions.
3️⃣ **CAD Editing & Modification**: Upload a DXF file to tweak dimensions, remove entities, or re-layer.
4️⃣ **3D STL Model Generation**: Build parametric 3D models ready for CNC machining or 3D printing.

Type your request below or ask a question to get started!`,
  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
};

export const use2DWorkspaceStore = create<Workspace2DState>((set, get) => ({
  activeFilePath: null,
  activeFileName: null,
  isDirty: false,

  dxfEntities: null,

  history: [],
  historyIndex: -1,

  width: 500,
  height: 500,
  toolDiameter: 6.0,

  activeView: 'Front',

  isGenerating: false,
  currentJobId: null,
  generatingStage: '',
  generatingProgress: 0,
  generatingMessage: '',

  chatMessages: [DEFAULT_WELCOME_MSG],
  attachments: [],

  inputErrors: {},

  widthDebounceTimer: null,
  heightDebounceTimer: null,

  setActiveFile: (filePath) => {
    const fileName = filePath ? filePath.split(/[/\\]/).pop() || null : null;
    set({ activeFilePath: filePath, activeFileName: fileName });
  },

  setDxfEntities: (dxfEntities) => {
    const currentEntities = get().dxfEntities;
    const history = get().history;
    const historyIndex = get().historyIndex;
    
    // Only add to history if entities actually changed
    if (JSON.stringify(currentEntities) !== JSON.stringify(dxfEntities)) {
      // Remove any future history if we're not at the end
      const newHistory = historyIndex >= 0 ? history.slice(0, historyIndex + 1) : history;
      
      // Add current state to history
      if (currentEntities) {
        newHistory.push(currentEntities);
      }
      
      // Limit history to 50 states
      if (newHistory.length > 50) {
        newHistory.shift();
      }
      
      set({ 
        dxfEntities, 
        history: newHistory, 
        historyIndex: newHistory.length - 1,
        isDirty: true 
      });
    } else {
      set({ dxfEntities });
    }
  },

  undo: () => {
    const { history, historyIndex } = get();
    if (historyIndex >= 0) {
      const previousState = history[historyIndex];
      set({ 
        dxfEntities: previousState, 
        historyIndex: historyIndex - 1,
        isDirty: true 
      });
    }
  },

  canUndo: () => {
    const { historyIndex } = get();
    return historyIndex >= 0;
  },

  redo: () => {
    // 2D undo stack is forward-only; redo not implemented
  },

  canRedo: () => false,

  setWidth: (width) => {
    const { dxfEntities, widthDebounceTimer } = get();
    
    // Clear existing debounce timer
    if (widthDebounceTimer) {
      clearTimeout(widthDebounceTimer);
    }
    
    // Update width immediately
    set((s) => ({ width, isDirty: true, inputErrors: { ...s.inputErrors, width: '' } }));
    
    // Debounce entity scaling
    const timer = setTimeout(() => {
      const { dxfEntities: currentEntities, height, setDxfEntities } = get();
      if (currentEntities && currentEntities.length > 0) {
        const scaled = scaleEntitiesToDimensions(currentEntities, width, height);
        if (scaled) {
          setDxfEntities(scaled);
        }
      }
    }, 300); // 300ms debounce
    
    set({ widthDebounceTimer: timer });
  },
  
  setHeight: (height) => {
    const { dxfEntities, heightDebounceTimer } = get();
    
    // Clear existing debounce timer
    if (heightDebounceTimer) {
      clearTimeout(heightDebounceTimer);
    }
    
    // Update height immediately
    set((s) => ({ height, isDirty: true, inputErrors: { ...s.inputErrors, height: '' } }));
    
    // Debounce entity scaling
    const timer = setTimeout(() => {
      const { dxfEntities: currentEntities, width, setDxfEntities } = get();
      if (currentEntities && currentEntities.length > 0) {
        const scaled = scaleEntitiesToDimensions(currentEntities, width, height);
        if (scaled) {
          setDxfEntities(scaled);
        }
      }
    }, 300); // 300ms debounce
    
    set({ heightDebounceTimer: timer });
  },
  
  setToolDiameter: (toolDiameter) => set((s) => ({ toolDiameter, isDirty: true, inputErrors: { ...s.inputErrors, toolDiameter: '' } })),

  setActiveView: (activeView) => set({ activeView }),

  setGenerating: (isGenerating, stage = '', progress = 0, message = '', jobId = null) => set({
    isGenerating,
    generatingStage: stage,
    generatingProgress: progress,
    generatingMessage: message,
    currentJobId: jobId,
  }),

  addChatMessage: (msg) => set((s) => {
    const isDuplicate = s.chatMessages.some((m) => m.id === msg.id);
    if (isDuplicate) return s;
    return { chatMessages: [...s.chatMessages, msg] };
  }),

  setChatMessages: (chatMessages) => set({ chatMessages }),

  addAttachment: (att) => set((s) => ({ attachments: [...s.attachments, att] })),
  removeAttachment: (id) => set((s) => ({ attachments: s.attachments.filter((a) => a.id !== id) })),
  clearAttachments: () => set({ attachments: [] }),

  validateInputs: () => {
    const { width, height, toolDiameter } = get();
    const errors: Record<string, string> = {};
    if (!width || isNaN(width) || width <= 0) errors.width = 'Width (X) is required and must be > 0';
    if (!height || isNaN(height) || height <= 0) errors.height = 'Height (Y) is required and must be > 0';
    if (!toolDiameter || isNaN(toolDiameter) || toolDiameter <= 0) errors.toolDiameter = 'Tool Diameter is required and must be > 0';
    set({ inputErrors: errors });
    return Object.keys(errors).length === 0;
  },

  markDirty: () => set({ isDirty: true }),

  saveWorkspace: async () => {
    const isValid = get().validateInputs();
    if (!isValid) return false;
    set({ isDirty: false });
    return true;
  },

  resetWorkspace: () => {
    set({
      activeFilePath: null,
      activeFileName: null,
      dxfEntities: null,
      isGenerating: false,
      currentJobId: null,
      generatingStage: '',
      generatingProgress: 0,
      generatingMessage: '',
      chatMessages: [DEFAULT_WELCOME_MSG],
      attachments: [],
      inputErrors: {},
    });
  },
}));
