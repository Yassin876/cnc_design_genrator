import { create } from 'zustand';
import { ChatMessage, FileAttachment, JobStageState } from '../../types';

export type ApplicationStatusState = 
  | 'empty'        // "No model loaded"
  | 'loading'      // "Preparing workspace"
  | 'generating'   // "AI is generating geometry"
  | 'processing'   // "Optimizing mesh"
  | 'validating'   // "Checking manufacturing constraints"
  | 'success'      // "Model ready"
  | 'error'        // "Generation failed"
  | 'uploading'    // "Uploading reference"
  | 'exporting'    // "Preparing STL"
  | 'cancelled';   // "Generation cancelled"

export interface StatusDetail {
  state: ApplicationStatusState;
  headline: string;
  subtext: string;
  badgeColor: string;
}

export const STATUS_LOOKUP: Record<ApplicationStatusState, StatusDetail> = {
  empty: {
    state: 'empty',
    headline: 'No model loaded',
    subtext: 'Create a new CAD design, open a project, or enter an AI prompt to start.',
    badgeColor: 'slate'
  },
  loading: {
    state: 'loading',
    headline: 'Preparing workspace',
    subtext: 'Initializing CAD rendering engine and loading workspace geometry...',
    badgeColor: 'blue'
  },
  generating: {
    state: 'generating',
    headline: 'AI is generating geometry',
    subtext: 'Deep learning pipeline synthesizing 3D parametric features and surface boundary paths.',
    badgeColor: 'indigo'
  },
  processing: {
    state: 'processing',
    headline: 'Optimizing mesh',
    subtext: 'Running non-manifold edge healing, face normal orientation, and polygon decimation.',
    badgeColor: 'violet'
  },
  validating: {
    state: 'validating',
    headline: 'Checking manufacturing constraints',
    subtext: 'Evaluating CNC tool clearance, wall thickness tolerances, and undercut geometries.',
    badgeColor: 'amber'
  },
  success: {
    state: 'success',
    headline: 'Model ready',
    subtext: 'Parametric CAD model compiled successfully and ready for engineering inspection.',
    badgeColor: 'emerald'
  },
  error: {
    state: 'error',
    headline: 'Generation failed',
    subtext: 'An error occurred during geometric synthesis. Review logs or adjust your prompt.',
    badgeColor: 'rose'
  },
  uploading: {
    state: 'uploading',
    headline: 'Uploading reference',
    subtext: 'Processing technical blueprint image or vector reference file...',
    badgeColor: 'sky'
  },
  exporting: {
    state: 'exporting',
    headline: 'Preparing export payload',
    subtext: 'Compiling target CAD file format (STL / STEP / DXF)...',
    badgeColor: 'cyan'
  },
  cancelled: {
    state: 'cancelled',
    headline: 'Generation cancelled',
    subtext: 'The AI generation request was aborted by user action.',
    badgeColor: 'zinc'
  }
};

interface AiState {
  appStatus: ApplicationStatusState;
  statusHeadline: string;
  statusSubtext: string;
  
  // SSE Pipeline state
  currentJobId: string | null;
  currentJobStage: JobStageState;
  progressPercent: number;
  stageMessage: string;
  errorMessage: string | null;

  // AI Chat & Prompts
  promptText: string;
  chatMessages: ChatMessage[];
  attachments: FileAttachment[];
  
  // Actions
  setAppStatus: (status: ApplicationStatusState, customHeadline?: string, customSubtext?: string) => void;
  setJobProgress: (jobId: string | null, stage: JobStageState, progress: number, message: string) => void;
  setError: (error: string) => void;
  setPromptText: (text: string) => void;
  addChatMessage: (msg: ChatMessage) => void;
  addAttachment: (att: FileAttachment) => void;
  removeAttachment: (id: string) => void;
  clearAttachments: () => void;
  resetAiState: () => void;
}

export const useAiStore = create<AiState>((set) => ({
  appStatus: 'empty',
  statusHeadline: STATUS_LOOKUP['empty'].headline,
  statusSubtext: STATUS_LOOKUP['empty'].subtext,

  currentJobId: null,
  currentJobStage: 'queued',
  progressPercent: 0,
  stageMessage: '',
  errorMessage: null,

  promptText: '',
  chatMessages: [
    {
      id: 'msg_welcome',
      sender: 'ai',
      text: 'Engineering Assistant initialized. Specify 3D parameters or describe required modifications.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ],
  attachments: [],

  setAppStatus: (status, customHeadline, customSubtext) => set({
    appStatus: status,
    statusHeadline: customHeadline || STATUS_LOOKUP[status].headline,
    statusSubtext: customSubtext || STATUS_LOOKUP[status].subtext,
    errorMessage: status === 'error' ? (customSubtext || 'Generation failed') : null
  }),

  setJobProgress: (currentJobId, currentJobStage, progressPercent, stageMessage) => {
    let appStatus: ApplicationStatusState = 'generating';
    if (currentJobStage === 'queued' || currentJobStage === 'processing' || currentJobStage === 'understanding') {
      appStatus = 'generating';
    } else if (currentJobStage === 'generating' || currentJobStage === 'geometry_processing') {
      appStatus = 'generating';
    } else if (currentJobStage === 'optimizing') {
      appStatus = 'processing';
    } else if (currentJobStage === 'validating') {
      appStatus = 'validating';
    } else if (currentJobStage === 'completed') {
      appStatus = 'success';
    } else if (currentJobStage === 'failed') {
      appStatus = 'error';
    } else if (currentJobStage === 'cancelled') {
      appStatus = 'cancelled';
    }

    set({
      currentJobId,
      currentJobStage,
      progressPercent,
      stageMessage,
      appStatus,
      statusHeadline: STATUS_LOOKUP[appStatus].headline,
      statusSubtext: stageMessage || STATUS_LOOKUP[appStatus].subtext
    });
  },

  setError: (errorMessage) => set({
    appStatus: 'error',
    errorMessage,
    statusHeadline: STATUS_LOOKUP['error'].headline,
    statusSubtext: errorMessage
  }),

  setPromptText: (promptText) => set({ promptText }),
  addChatMessage: (msg) => set((s) => ({ chatMessages: [...s.chatMessages, msg] })),
  addAttachment: (att) => set((s) => ({ attachments: [...s.attachments, att] })),
  removeAttachment: (id) => set((s) => ({ attachments: s.attachments.filter((a) => a.id !== id) })),
  clearAttachments: () => set({ attachments: [] }),
  resetAiState: () => set({
    appStatus: 'empty',
    statusHeadline: STATUS_LOOKUP['empty'].headline,
    statusSubtext: STATUS_LOOKUP['empty'].subtext,
    currentJobId: null,
    progressPercent: 0,
    stageMessage: '',
    errorMessage: null
  })
}));
