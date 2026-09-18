import { create } from 'zustand';
import { ViewMode, MeshInspection, ValidationReport, ChatMessage, JobStageState, ProjectVersion, TreeNode, ModelTransform, FileAttachment } from '../../types';
import { use2DWorkspaceStore } from './use2DWorkspaceStore';

interface WorkspaceState {
  viewMode: ViewMode;
  activeFilePath: string | null;
  activeFileName: string | null;
  activeProjectId: string | null;
  activeProjectName: string | null;
  designType: '2D' | '3D';
  dxfContent: string | null;  // For in-memory DXF content from external API
  
  // Real-Time Job SSE Progress State
  isGenerating: boolean;
  currentJobId: string | null;
  currentJobStage: JobStageState;
  currentJobProgress: number;
  currentJobMessage: string;
  generationStatusText: string;

  // Viewport Render & Shading Settings
  renderStyle: 'solid' | 'wireframe' | 'shaded_edges' | 'clay' | 'normal';
  renderMaterial: string;
  cameraPreset: 'top' | 'bottom' | 'front' | 'back' | 'left' | 'right' | 'iso';

  showWireframe: boolean;

  // CAD Viewport Overlays
  showGrid: boolean;
  showAxes: boolean;
  showViewCube: boolean;
  showAxisIndicator: boolean;
  showSelectionOutline: boolean;
  showMeasurements: boolean;

  // Left Panel Tab State
  leftPanelTab: 'ai' | 'tree';

  // Model Tree Structure
  treeNodes: TreeNode[];
  selectedNodeId: string | null;

  // Transform & Engineering Context State
  modelTransform: ModelTransform;
  units: 'mm' | 'in' | 'cm' | 'm';
  material: string;
  parameters: Record<string, any>;
  previousOperations: string[];

  // Attachments for AI Assistant
  attachments: FileAttachment[];

  // CAD Data & Version History Stack
  inspectionData: MeshInspection | null;
  dxfEntities: any[] | null;
  validationReport: ValidationReport | null;
  projectVersions: ProjectVersion[];

  // AI Chat
  chatMessages: ChatMessage[];
  
  // Modals
  isExportModalOpen: boolean;
  isValidatingModalOpen: boolean;
  isNestingModalOpen: boolean;
  isImportModalOpen: boolean;
  isNewProjectModalOpen: boolean;
  isAuthModalOpen: boolean;
  isVersionHistoryModalOpen: boolean;

  // Actions
  setViewMode: (mode: ViewMode) => void;
  setActiveProjectId: (id: string | null, name?: string | null) => void;
  loadFile: (filePath: string, type: '2D' | '3D', projectId?: string, projectName?: string) => void;
  loadDXFContent: (dxfContent: string, fileName?: string) => void;
  setDxfContent: (dxfContent: string | null) => void;
  setGeneratingProgress: (isGenerating: boolean, stage?: JobStageState, progress?: number, message?: string, jobId?: string) => void;
  setRenderStyle: (style: 'solid' | 'wireframe' | 'shaded_edges' | 'clay' | 'normal') => void;
  setCameraPreset: (preset: 'top' | 'bottom' | 'front' | 'back' | 'left' | 'right' | 'iso') => void;
  toggleWireframe: () => void;
  toggleGrid: () => void;
  toggleAxes: () => void;
  toggleViewCube: () => void;
  toggleAxisIndicator: () => void;
  toggleSelectionOutline: () => void;
  toggleMeasurements: () => void;
  setLeftPanelTab: (tab: 'ai' | 'tree') => void;
  
  // Tree Actions
  setTreeNodes: (nodes: TreeNode[]) => void;
  selectTreeNode: (id: string | null) => void;
  toggleNodeVisibility: (id: string) => void;
  renameTreeNode: (id: string, name: string) => void;
  isolateTreeNode: (id: string) => void;
  deleteTreeNode: (id: string) => void;
  toggleNodeExpand: (id: string) => void;

  // Transform Actions
  setTransform: (transform: Partial<ModelTransform>) => void;
  setUnits: (units: 'mm' | 'in' | 'cm' | 'm') => void;
  setMaterial: (material: string) => void;
  setParameter: (key: string, value: any) => void;

  // Attachments Actions
  addAttachment: (att: FileAttachment) => void;
  removeAttachment: (id: string) => void;
  clearAttachments: () => void;

  setInspectionData: (data: MeshInspection | null) => void;
  setDxfEntities: (entities: any[] | null) => void;
  setValidationReport: (report: ValidationReport | null) => void;
  setProjectVersions: (versions: ProjectVersion[]) => void;
  addChatMessage: (message: ChatMessage) => void;
  setExportModalOpen: (open: boolean) => void;
  setValidatingModalOpen: (open: boolean) => void;
  setNestingModalOpen: (open: boolean) => void;
  setImportModalOpen: (open: boolean) => void;
  setNewProjectModalOpen: (open: boolean) => void;
  setAuthModalOpen: (open: boolean) => void;
  setVersionHistoryModalOpen: (open: boolean) => void;
}

const defaultTree: TreeNode[] = [
  {
    id: 'proj_root',
    name: 'Industrial Pipe Elbow Assembly',
    type: 'Project',
    visible: true,
    expanded: true,
    children: [
      {
        id: 'asm_main',
        name: 'Main Assembly',
        type: 'Assembly',
        visible: true,
        expanded: true,
        children: [
          { id: 'body_1', name: 'Pipe Main Body', type: 'Body', visible: true, properties: { material: 'Industrial Steel' } },
          { id: 'flange_1', name: 'Mounting Flange', type: 'Flange', visible: true, properties: { dimensions: { thickness: 12, diameter: 110 } } },
          { id: 'hole_group', name: '4x M8 Mounting Holes', type: 'Hole', visible: true, properties: { dimensions: { diameter: 8 } } },
          { id: 'fillet_1', name: 'Transition Fillet (R5)', type: 'Fillet', visible: true, properties: { dimensions: { radius: 5 } } },
          { id: 'surf_inner', name: 'Inner Flow Surface', type: 'Surface', visible: true, properties: { dimensions: { inner_diameter: 50 } } }
        ]
      }
    ]
  }
];

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  viewMode: 'auth',
  activeFilePath: null,
  activeFileName: null,
  designType: '2D',
  dxfContent: null,

  isGenerating: false,
  currentJobId: null,
  currentJobStage: 'queued',
  currentJobProgress: 0,
  currentJobMessage: '',
  generationStatusText: 'Ready',

  renderStyle: 'solid',
  renderMaterial: 'Standard Steel',
  cameraPreset: 'iso',

  showWireframe: false,

  showGrid: true,
  showAxes: true,
  showViewCube: true,
  showAxisIndicator: true,
  showSelectionOutline: true,
  showMeasurements: true,

  leftPanelTab: 'ai',

  treeNodes: defaultTree,
  selectedNodeId: 'body_1',

  modelTransform: {
    position: { x: 0, y: 0, z: 0 },
    rotation: { x: 0, y: 0, z: 0 },
    scale: { x: 1, y: 1, z: 1 }
  },
  units: 'mm',
  material: 'Industrial Steel 304',
  parameters: {
    // 3D parameters
    inner_diameter: 50,
    wall_thickness: 5,
    bend_angle: 90,
    flange_outer_diameter: 110,
    mounting_holes: 4,
    hole_diameter: 8,
    // 2D parameters
    width: 700.0,
    height: 700.0,
    tool_diameter_mm: 5.0
  },
  previousOperations: [
    'Create 90-degree industrial steel pipe elbow (50mm ID, 5mm wall)',
    'Add mounting flange'
  ],

  attachments: [],

  inspectionData: null,
  dxfEntities: null,
  validationReport: null,
  projectVersions: [],

  chatMessages: [
    {
      id: 'msg_welcome',
      sender: 'ai',
      text: 'Welcome to the 2D DXF workspace. Upload an image or describe a part to generate a CAD-ready blueprint.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ],

  activeProjectId: null,
  activeProjectName: null,

  isExportModalOpen: false,
  isValidatingModalOpen: false,
  isNestingModalOpen: false,
  isImportModalOpen: false,
  isNewProjectModalOpen: false,
  isAuthModalOpen: false,
  isVersionHistoryModalOpen: false,

  setViewMode: (viewMode) => {
    const currentMode = get().viewMode;
    if (viewMode === 'workspace_2d' && currentMode !== 'workspace_2d') {
      use2DWorkspaceStore.getState().resetWorkspace();
      set({
        viewMode,
        activeProjectId: null,
        activeProjectName: null,
        activeFilePath: null,
        activeFileName: null,
        dxfContent: null
      });
      return;
    }
    set({ viewMode });
  },
  setActiveProjectId: (activeProjectId, activeProjectName = null) => set({ activeProjectId, activeProjectName }),
  loadFile: (activeFilePath, designType, projectId, projectName) => {
    if (designType === '2D') {
      use2DWorkspaceStore.getState().setActiveFile(activeFilePath);
    }
    set((s) => ({
      activeFilePath,
      activeFileName: activeFilePath.split(/[/\\]/).pop() || 'Untitled',
      activeProjectId: projectId !== undefined ? projectId : s.activeProjectId,
      activeProjectName: projectName !== undefined ? projectName : s.activeProjectName,
      designType,
      viewMode: designType === '3D' ? 'workspace_3d' : 'workspace_2d'
    }));
  },
  loadDXFContent: (dxfContent, fileName = 'generated.dxf') => set({
    activeFilePath: null,  // No local file path for external API content
    activeFileName: fileName,
    designType: '2D',
    viewMode: 'workspace_2d',
    dxfContent: dxfContent  // Store DXF content in memory
  }),
  setDxfContent: (dxfContent) => set({ dxfContent }),
  setGeneratingProgress: (isGenerating, currentJobStage = 'queued', currentJobProgress = 0, currentJobMessage = '', currentJobId = null) => 
    set({ isGenerating, currentJobStage, currentJobProgress, currentJobMessage, currentJobId }),
  setRenderStyle: (renderStyle) => set({ renderStyle }),
  setCameraPreset: (cameraPreset) => set({ cameraPreset }),
  toggleWireframe: () => set((s) => ({ showWireframe: !s.showWireframe })),
  toggleGrid: () => set((s) => ({ showGrid: !s.showGrid })),
  toggleAxes: () => set((s) => ({ showAxes: !s.showAxes })),
  toggleViewCube: () => set((s) => ({ showViewCube: !s.showViewCube })),
  toggleAxisIndicator: () => set((s) => ({ showAxisIndicator: !s.showAxisIndicator })),
  toggleSelectionOutline: () => set((s) => ({ showSelectionOutline: !s.showSelectionOutline })),
  toggleMeasurements: () => set((s) => ({ showMeasurements: !s.showMeasurements })),
  setLeftPanelTab: (leftPanelTab) => set({ leftPanelTab }),

  // Tree Actions Implementation
  setTreeNodes: (treeNodes) => set({ treeNodes }),
  selectTreeNode: (selectedNodeId) => set({ selectedNodeId }),
  toggleNodeVisibility: (id) => set((state) => {
    const toggleVis = (nodes: TreeNode[]): TreeNode[] =>
      nodes.map((n) => {
        if (n.id === id) return { ...n, visible: !n.visible };
        if (n.children) return { ...n, children: toggleVis(n.children) };
        return n;
      });
    return { treeNodes: toggleVis(state.treeNodes) };
  }),
  renameTreeNode: (id, newName) => set((state) => {
    const rename = (nodes: TreeNode[]): TreeNode[] =>
      nodes.map((n) => {
        if (n.id === id) return { ...n, name: newName };
        if (n.children) return { ...n, children: rename(n.children) };
        return n;
      });
    return { treeNodes: rename(state.treeNodes) };
  }),
  isolateTreeNode: (id) => set((state) => {
    const isolate = (nodes: TreeNode[]): TreeNode[] =>
      nodes.map((n) => ({
        ...n,
        visible: n.id === id,
        children: n.children ? isolate(n.children) : undefined
      }));
    return { treeNodes: isolate(state.treeNodes), selectedNodeId: id };
  }),
  deleteTreeNode: (id) => set((state) => {
    const del = (nodes: TreeNode[]): TreeNode[] =>
      nodes
        .filter((n) => n.id !== id)
        .map((n) => ({ ...n, children: n.children ? del(n.children) : undefined }));
    return { treeNodes: del(state.treeNodes), selectedNodeId: state.selectedNodeId === id ? null : state.selectedNodeId };
  }),
  toggleNodeExpand: (id) => set((state) => {
    const toggleExp = (nodes: TreeNode[]): TreeNode[] =>
      nodes.map((n) => {
        if (n.id === id) return { ...n, expanded: !n.expanded };
        if (n.children) return { ...n, children: toggleExp(n.children) };
        return n;
      });
    return { treeNodes: toggleExp(state.treeNodes) };
  }),

  // Transform Actions Implementation
  setTransform: (t) => set((state) => ({
    modelTransform: {
      position: { ...state.modelTransform.position, ...t.position },
      rotation: { ...state.modelTransform.rotation, ...t.rotation },
      scale: { ...state.modelTransform.scale, ...t.scale }
    }
  })),
  setUnits: (units) => set({ units }),
  setMaterial: (material) => set({ material }),
  setParameter: (key, val) => set((state) => ({
    parameters: { ...state.parameters, [key]: val }
  })),

  // Attachments Actions Implementation
  addAttachment: (att) => set((state) => ({ attachments: [...state.attachments, att] })),
  removeAttachment: (id) => set((state) => ({ attachments: state.attachments.filter((a) => a.id !== id) })),
  clearAttachments: () => set({ attachments: [] }),

  setInspectionData: (inspectionData) => set({ inspectionData }),
  setDxfEntities: (dxfEntities) => set({ dxfEntities }),
  setValidationReport: (validationReport) => set({ validationReport }),
  setProjectVersions: (projectVersions) => set({ projectVersions }),
  addChatMessage: (msg) => set((s) => ({ chatMessages: [...s.chatMessages, msg] })),
  setExportModalOpen: (isExportModalOpen) => set({ isExportModalOpen }),
  setValidatingModalOpen: (isValidatingModalOpen) => set({ isValidatingModalOpen }),
  setNestingModalOpen: (isNestingModalOpen) => set({ isNestingModalOpen }),
  setImportModalOpen: (isImportModalOpen) => set({ isImportModalOpen }),
  setNewProjectModalOpen: (isNewProjectModalOpen) => set({ isNewProjectModalOpen }),
  setAuthModalOpen: (isAuthModalOpen) => set({ isAuthModalOpen }),
  setVersionHistoryModalOpen: (isVersionHistoryModalOpen) => set({ isVersionHistoryModalOpen }),
}));

