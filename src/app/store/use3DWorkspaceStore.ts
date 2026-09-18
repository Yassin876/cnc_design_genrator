import { create } from 'zustand';
import { ChatMessage, FileAttachment, TreeNode } from '../../types';
import { apiClient } from '../../services/api/client';

export interface Part3D {
  id: string;
  name: string;
  filePath?: string;
  visible: boolean;
  isAssembled: boolean;
  dimensions: {
    length: number;
    width: number;
    height: number;
  };
  position: {
    x: number;
    y: number;
    z: number;
  };
  color?: string;
}

export interface Workspace3DState {
  // File & Project
  activeFilePath: string | null;
  activeFileName: string | null;
  isDirty: boolean;

  // 3D Global / Default Parameters
  length: number;
  width: number;
  height: number;

  // Model Tree (parts + assembly) – 3D ONLY
  parts: Part3D[];
  treeNodes: TreeNode[];
  selectedNodeId: string | null;
  assemblyMode: boolean;

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

  // Actions
  setActiveFile: (filePath: string | null) => void;
  setLength: (val: number) => void;
  setWidth: (val: number) => void;
  setHeight: (val: number) => void;
  setGenerating: (isGenerating: boolean, stage?: string, progress?: number, message?: string, jobId?: string | null) => void;
  addChatMessage: (msg: ChatMessage) => void;
  setChatMessages: (msgs: ChatMessage[]) => void;
  addAttachment: (att: FileAttachment) => void;
  removeAttachment: (id: string) => void;
  clearAttachments: () => void;

  // Model Tree Actions
  addNewPart: (name?: string) => void;
  addPart: (part: Part3D) => void;
  removePart: (id: string) => void;
  renamePart: (id: string, newName: string) => void;
  togglePartVisibility: (id: string) => void;
  updatePartDimensions: (id: string, dims: Partial<Part3D['dimensions']>) => void;
  updatePartPosition: (id: string, pos: Partial<Part3D['position']>) => void;
  setSelectedNodeId: (id: string | null) => void;
  selectNode: (id: string | null) => void;
  setAssemblyMode: (enabled: boolean) => void;
  toggleAssemblyMode: () => void;

  validateInputs: () => boolean;
  markDirty: () => void;
  saveWorkspace: () => Promise<boolean>;
  resetWorkspace: () => void;
  // History & Undo / Redo
  history: Workspace3DSnapshot[];
  future: Workspace3DSnapshot[];
  canUndo: () => boolean;
  undo: () => void;
  canRedo: () => boolean;
  redo: () => void;
}

export interface Workspace3DSnapshot {
  length: number;
  width: number;
  height: number;
  parts: Part3D[];
  treeNodes: TreeNode[];
  selectedNodeId: string | null;
  activeFilePath: string | null;
}

const DEFAULT_WELCOME_MSG_3D: ChatMessage = {
  id: 'welcome_3d',
  sender: 'ai',
  text: `👋 Welcome to the 3D Workspace! I am **Anti Design**.

You can request custom 3D STL models or parametric modifications ready for CNC machining & 3D printing!`,
  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
};

const DEFAULT_PARTS: Part3D[] = [
  {
    id: 'part-main',
    name: 'Main Body',
    visible: true,
    isAssembled: true,
    dimensions: { length: 100, width: 100, height: 50 },
    position: { x: 0, y: 0, z: 0 },
    color: '#9ca3af'  // neutral gray — CAD-standard
  }
];

const takeSnapshot = (s: Workspace3DState): Workspace3DSnapshot => ({
  length: s.length,
  width: s.width,
  height: s.height,
  parts: JSON.parse(JSON.stringify(s.parts)),
  treeNodes: JSON.parse(JSON.stringify(s.treeNodes)),
  selectedNodeId: s.selectedNodeId,
  activeFilePath: s.activeFilePath
});

/** Push current state onto history stack and clear future (redo) stack. */
const pushHistory = (set: (fn: (s: Workspace3DState) => Partial<Workspace3DState>) => void, snapshot: Workspace3DSnapshot) => {
  set((s) => ({
    history: [...s.history, snapshot].slice(-50),
    future: []
  }));
};

export const use3DWorkspaceStore = create<Workspace3DState>((set, get) => ({
  activeFilePath: null,
  activeFileName: null,
  isDirty: false,

  length: 100,
  width: 100,
  height: 50,

  parts: DEFAULT_PARTS,
  treeNodes: [
    {
      id: 'part-main',
      name: 'Main Body',
      type: 'Body',
      visible: true
    }
  ],
  selectedNodeId: 'part-main',
  assemblyMode: false,

  history: [],
  future: [],

  isGenerating: false,
  currentJobId: null,
  generatingStage: '',
  generatingProgress: 0,
  generatingMessage: '',

  chatMessages: [DEFAULT_WELCOME_MSG_3D],
  attachments: [],

  inputErrors: {},

  setActiveFile: (filePath) => {
    const fileName = filePath ? filePath.split(/[/\\]/).pop() || null : null;
    set((s) => {
      let updatedParts = [...s.parts];
      if (filePath) {
        const selIdx = s.parts.findIndex(p => p.id === s.selectedNodeId);
        const targetIdx = selIdx >= 0 ? selIdx : 0;
        if (targetIdx >= 0 && updatedParts[targetIdx]) {
          updatedParts[targetIdx] = {
            ...updatedParts[targetIdx],
            filePath,
            name: updatedParts[targetIdx].name === 'Main Body' ? (fileName || '3D Model') : updatedParts[targetIdx].name
          };
        } else {
          updatedParts = [
            {
              id: 'part-main',
              name: fileName || '3D Model',
              filePath,
              visible: true,
              isAssembled: true,
              dimensions: { length: s.length, width: s.width, height: s.height },
              position: { x: 0, y: 0, z: 0 },
              color: '#9ca3af'
            }
          ];
        }
      }
      return {
        activeFilePath: filePath,
        activeFileName: fileName,
        parts: updatedParts,
        treeNodes: updatedParts.map((p) => ({
          id: p.id,
          name: p.name,
          type: 'Body',
          visible: p.visible
        }))
      };
    });
  },

  setLength: (length) => {
    const snap = takeSnapshot(get());
    pushHistory(set, snap);
    const { selectedNodeId } = get();
    set((s) => ({ length, isDirty: true, inputErrors: { ...s.inputErrors, length: '' } }));
    if (selectedNodeId) {
      get().updatePartDimensions(selectedNodeId, { length });
    }
  },

  setWidth: (width) => {
    const snap = takeSnapshot(get());
    pushHistory(set, snap);
    const { selectedNodeId } = get();
    set((s) => ({ width, isDirty: true, inputErrors: { ...s.inputErrors, width: '' } }));
    if (selectedNodeId) {
      get().updatePartDimensions(selectedNodeId, { width });
    }
  },

  setHeight: (height) => {
    const snap = takeSnapshot(get());
    pushHistory(set, snap);
    const { selectedNodeId } = get();
    set((s) => ({ height, isDirty: true, inputErrors: { ...s.inputErrors, height: '' } }));
    if (selectedNodeId) {
      get().updatePartDimensions(selectedNodeId, { height });
    }
  },

  setGenerating: (isGenerating, stage = '', progress = 0, message = '', jobId = null) => set({
    isGenerating,
    generatingStage: stage,
    generatingProgress: progress,
    generatingMessage: message,
    currentJobId: jobId
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

  addNewPart: (name) => {
    pushHistory(set, takeSnapshot(get()));
    return set((s) => {
    const partCount = s.parts.length + 1;
    const partName = name || `Part ${partCount}`;
    const newPartId = `part-${Date.now()}`;
    const colors = ['#9ca3af', '#a1a1aa', '#94a3b8', '#b0b7c3', '#8d99ae', '#adb5bd'];
    const color = colors[partCount % colors.length];

    // Offset new part slightly so it is visibly distinct
    const offsetX = (s.parts.length % 3) * 30;
    const offsetY = Math.floor(s.parts.length / 3) * 30;

    const newPart: Part3D = {
      id: newPartId,
      name: partName,
      visible: true,
      isAssembled: true,
      dimensions: { length: 60, width: 60, height: 40 },
      position: { x: offsetX, y: offsetY, z: 0 },
      color
    };

    const updatedParts = [...s.parts, newPart];
    const nodes: TreeNode[] = updatedParts.map((p) => ({
      id: p.id,
      name: p.name,
      type: 'Body',
      visible: p.visible
    }));

    return {
      parts: updatedParts,
      treeNodes: nodes,
      selectedNodeId: newPartId,
      length: newPart.dimensions.length,
      width: newPart.dimensions.width,
      height: newPart.dimensions.height,
      isDirty: true
    };
  });  },

  addPart: (part) => set((s) => {
    const updated = [...s.parts.filter(p => p.id !== part.id), part];
    const nodes: TreeNode[] = updated.map(p => ({
      id: p.id,
      name: p.name,
      type: 'Body',
      visible: p.visible
    }));
    return { parts: updated, treeNodes: nodes, isDirty: true };
  }),

  removePart: (id) => {
    pushHistory(set, takeSnapshot(get()));
    return set((s) => {
    const updatedParts = s.parts.filter(p => p.id !== id);
    const nodes = s.treeNodes.filter(n => n.id !== id);
    const nextSelected = s.selectedNodeId === id ? (updatedParts[0]?.id || null) : s.selectedNodeId;
    const activePart = updatedParts.find(p => p.id === nextSelected);

    return {
      parts: updatedParts,
      treeNodes: nodes,
      selectedNodeId: nextSelected,
      length: activePart?.dimensions.length || s.length,
      width: activePart?.dimensions.width || s.width,
      height: activePart?.dimensions.height || s.height,
      isDirty: true
    };
  });  },

  renamePart: (id, newName) => {
    pushHistory(set, takeSnapshot(get()));
    set((s) => ({
      parts: s.parts.map(p => p.id === id ? { ...p, name: newName } : p),
      treeNodes: s.treeNodes.map(n => n.id === id ? { ...n, name: newName } : n),
      isDirty: true
    }));
  },

  togglePartVisibility: (id) => set((s) => ({
    parts: s.parts.map(p => p.id === id ? { ...p, visible: !p.visible } : p),
    treeNodes: s.treeNodes.map(n => n.id === id ? { ...n, visible: !n.visible } : n),
    isDirty: true
  })),

  updatePartDimensions: (id, dims) => set((s) => {
    const updated = s.parts.map(p => {
      if (p.id !== id) return p;
      return {
        ...p,
        dimensions: {
          ...p.dimensions,
          ...dims
        }
      };
    });
    return { parts: updated, isDirty: true };
  }),

  updatePartPosition: (id, pos) => set((s) => {
    const updated = s.parts.map(p => {
      if (p.id !== id) return p;
      return {
        ...p,
        position: {
          ...p.position,
          ...pos
        }
      };
    });
    return { parts: updated, isDirty: true };
  }),

  setSelectedNodeId: (id) => {
    const part = get().parts.find(p => p.id === id);
    set({
      selectedNodeId: id,
      length: part ? part.dimensions.length : get().length,
      width: part ? part.dimensions.width : get().width,
      height: part ? part.dimensions.height : get().height
    });
  },

  selectNode: (id) => {
    get().setSelectedNodeId(id);
  },

  setAssemblyMode: (assemblyMode) => set({ assemblyMode }),
  toggleAssemblyMode: () => set((s) => ({ assemblyMode: !s.assemblyMode })),

  validateInputs: () => {
    const { length, width, height } = get();
    const errors: Record<string, string> = {};
    if (!length || isNaN(length) || length <= 0) errors.length = 'Length (X) must be > 0';
    if (!width || isNaN(width) || width <= 0) errors.width = 'Width (Y) must be > 0';
    if (!height || isNaN(height) || height <= 0) errors.height = 'Height (Z) must be > 0';
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

  canUndo: () => get().history.length > 0,
  canRedo: () => get().future.length > 0,

  undo: () => {
    const { history, future } = get();
    if (history.length === 0) return;
    const previous = history[history.length - 1];
    const currentSnap = takeSnapshot(get());
    set({
      length: previous.length,
      width: previous.width,
      height: previous.height,
      parts: previous.parts,
      treeNodes: previous.treeNodes,
      selectedNodeId: previous.selectedNodeId,
      activeFilePath: previous.activeFilePath,
      history: history.slice(0, -1),
      future: [currentSnap, ...future].slice(0, 50),
      isDirty: true
    });
  },

  redo: () => {
    const { history, future } = get();
    if (future.length === 0) return;
    const next = future[0];
    const currentSnap = takeSnapshot(get());
    set({
      length: next.length,
      width: next.width,
      height: next.height,
      parts: next.parts,
      treeNodes: next.treeNodes,
      selectedNodeId: next.selectedNodeId,
      activeFilePath: next.activeFilePath,
      history: [...history, currentSnap].slice(-50),
      future: future.slice(1),
      isDirty: true
    });
  },

  resetWorkspace: () => {
    set({
      activeFilePath: null,
      activeFileName: null,
      parts: DEFAULT_PARTS,
      treeNodes: [
        {
          id: 'part-main',
          name: 'Main Body',
          type: 'Body',
          visible: true
        }
      ],
      selectedNodeId: 'part-main',
      history: [],
      future: [],
      isGenerating: false,
      currentJobId: null,
      generatingStage: '',
      generatingProgress: 0,
      generatingMessage: '',
      chatMessages: [DEFAULT_WELCOME_MSG_3D],
      attachments: [],
      inputErrors: {}
    });
  },
}));
