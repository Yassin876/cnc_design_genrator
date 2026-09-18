import { vi } from 'vitest';

// vi.mock() factories are hoisted above all variable declarations, so referencing
// a const/let declared after them causes "Cannot access before initialization".
// vi.hoisted() creates variables that are safe to reference inside factory closures.
const {
  mockApiClientPost,
  mockTextTo3D,
  mockImageTo3D,
  mockEdit3D,
  mockTextTo2D,
  mockImageTo2D,
  mockStreamJobProgress,
  mockSaveProjectMessage,
  mockGetProjectMessages,
} = vi.hoisted(() => ({
  mockApiClientPost: vi.fn(),
  mockTextTo3D: vi.fn(),
  mockImageTo3D: vi.fn(),
  mockEdit3D: vi.fn(),
  mockTextTo2D: vi.fn(),
  mockImageTo2D: vi.fn(),
  mockStreamJobProgress: vi.fn(),
  mockSaveProjectMessage: vi.fn(),
  mockGetProjectMessages: vi.fn(),
}));

vi.mock('../../../app/store/useWorkspaceStore', () => ({ useWorkspaceStore: vi.fn() }));
vi.mock('../../../app/store/use2DWorkspaceStore', () => ({ use2DWorkspaceStore: vi.fn() }));
vi.mock('../../../app/store/use3DWorkspaceStore', () => ({ use3DWorkspaceStore: vi.fn() }));
vi.mock('../../../app/store/useAuthStore', () => ({ useAuthStore: vi.fn() }));

vi.mock('../../../services/api/client', () => ({
  apiClient: {
    post: mockApiClientPost,
    defaults: { baseURL: 'http://localhost:8000/api/v1' },
  },
  getStaticFileUrl: vi.fn((p: string) => `http://localhost:8000/static/${p}`),
}));

vi.mock('../../../services/api/generation', () => ({
  generationApiService: {
    textTo3D: mockTextTo3D,
    imageTo3D: mockImageTo3D,
    edit3D: mockEdit3D,
    textTo2D: mockTextTo2D,
    imageTo2D: mockImageTo2D,
    streamJobProgress: mockStreamJobProgress,
  },
}));

vi.mock('../../../services/api/projects', () => ({
  projectsApiService: {
    saveProjectMessage: mockSaveProjectMessage,
    getProjectMessages: mockGetProjectMessages,
  },
}));

vi.mock('../../../components/dialogs/SaveProjectModal', () => ({ SaveProjectModal: () => null }));

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useWorkspaceStore } from '../../../app/store/useWorkspaceStore';
import { use2DWorkspaceStore } from '../../../app/store/use2DWorkspaceStore';
import { use3DWorkspaceStore } from '../../../app/store/use3DWorkspaceStore';
import { useAuthStore } from '../../../app/store/useAuthStore';
import { AIAssistantSidebar } from './AIAssistantSidebar';

const QUEUED_JOB = { job_id: 'job_queued_999', status: 'queued', message: 'Queued' };
const COMPLETED_JOB_3D = {
  job_id: 'job_done_3d',
  status: 'completed',
  message: 'Done',
  output_file_path: '/storage/outputs/test.stl',
  output_filename: 'test.stl',
};

function makeStore3D(overrides: Record<string, any> = {}) {
  const base = {
    chatMessages: [], attachments: [], isGenerating: false,
    generatingProgress: 15, generatingStage: 'analyzing', generatingMessage: '',
    activeFilePath: null, height: 50, width: 100, length: 100, parts: [], inputErrors: {},
    addChatMessage: vi.fn(), addAttachment: vi.fn(), removeAttachment: vi.fn(),
    clearAttachments: vi.fn(), setGenerating: vi.fn(), setActiveFile: vi.fn(),
    addPart: vi.fn(), resetWorkspace: vi.fn(), validateInputs: vi.fn(() => true),
    setChatMessages: vi.fn(),
    ...overrides,
  };
  vi.mocked(use3DWorkspaceStore).mockReturnValue(base as any);
  return base;
}

function setupCommon() {
  vi.mocked(useWorkspaceStore).mockReturnValue({
    viewMode: 'workspace_3d', setExportModalOpen: vi.fn(),
    loadDXFContent: vi.fn(), activeProjectId: null,
    activeProjectName: null, setActiveProjectId: vi.fn(),
  } as any);
  (useWorkspaceStore as any).getState = () => ({ activeProjectId: null });
  vi.mocked(useAuthStore).mockReturnValue({ user: { id: 'route_test_user' } } as any);
  vi.mocked(use2DWorkspaceStore).mockReturnValue({
    chatMessages: [], attachments: [], isGenerating: false,
    addChatMessage: vi.fn(), inputErrors: {}, setChatMessages: vi.fn(),
  } as any);
  mockSaveProjectMessage.mockResolvedValue({});
  mockGetProjectMessages.mockResolvedValue([]);
  mockStreamJobProgress.mockReturnValue({ onmessage: null, onerror: null, close: vi.fn() });
}

describe('Routing — text / image / image+text endpoint mapping', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupCommon();
  });

  it('Case 1 — text only -> calls textTo3D exclusively', async () => {
    makeStore3D({ attachments: [] });
    mockApiClientPost.mockImplementation(async (url: string) => {
      if (url === '/generation/intent') {
        return { data: { intent: 'generate_3d', reply_text: '', prompt_payload: 'a bolt', status: 'ok' } };
      }
      throw new Error(`Unexpected POST: ${url}`);
    });
    mockTextTo3D.mockResolvedValue(QUEUED_JOB);

    render(<AIAssistantSidebar />);
    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText(/Describe.*3D/i), 'a bolt');
    const send = screen.getAllByRole('button').find(b => b.querySelector('.lucide-send'));
    await user.click(send!);

    await waitFor(() => expect(mockTextTo3D).toHaveBeenCalledTimes(1));
    expect(mockImageTo3D).not.toHaveBeenCalled();
    expect(mockImageTo2D).not.toHaveBeenCalled();
    const editCalls = mockApiClientPost.mock.calls.filter(([u]) => u === '/editing/ai');
    expect(editCalls).toHaveLength(0);
    expect(mockTextTo3D).toHaveBeenCalledWith(expect.objectContaining({ prompt: 'a bolt' }));
  });

  it('Case 2 — image only -> calls imageTo3D exclusively', async () => {
    makeStore3D({
      attachments: [{
        id: 'att1', filename: 'part.png', file_path: '/storage/uploads/part.png',
        file_size: 1024, format: 'PNG', upload_timestamp: '12:00',
      }],
    });
    mockApiClientPost.mockImplementation(async (url: string) => {
      if (url === '/generation/intent') {
        return { data: { intent: 'image_to_cad', reply_text: '', prompt_payload: '', status: 'ok' } };
      }
      throw new Error(`Unexpected POST: ${url}`);
    });
    mockImageTo3D.mockResolvedValue(QUEUED_JOB);

    render(<AIAssistantSidebar />);
    const user = userEvent.setup();
    const send = screen.getAllByRole('button').find(b => b.querySelector('.lucide-send'));
    await user.click(send!);

    await waitFor(() => expect(mockImageTo3D).toHaveBeenCalledTimes(1));
    expect(mockTextTo3D).not.toHaveBeenCalled();
    expect(mockTextTo2D).not.toHaveBeenCalled();
    const editCalls = mockApiClientPost.mock.calls.filter(([u]) => u === '/editing/ai');
    expect(editCalls).toHaveLength(0);
    expect(mockImageTo3D).toHaveBeenCalledWith(
      expect.objectContaining({ image_path: '/storage/uploads/part.png' })
    );
  });

  it('Case 3 — CAD attachment + text -> calls edit3D exclusively', async () => {
    makeStore3D({
      activeFilePath: '/storage/outputs/existing.stl',
      attachments: [{
        id: 'att2', filename: 'part.stl', file_path: '/storage/uploads/part.stl',
        file_size: 2048, format: 'STL', upload_timestamp: '12:00',
      }],
    });
    mockApiClientPost.mockImplementation(async (url: string) => {
      if (url === '/generation/intent') {
        return { data: { intent: 'edit_3d', reply_text: '', prompt_payload: 'add fillet', status: 'ok' } };
      }
      throw new Error(`Unexpected POST: ${url}`);
    });
    mockEdit3D.mockResolvedValue(COMPLETED_JOB_3D);

    render(<AIAssistantSidebar />);
    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText(/Describe.*3D/i), 'add fillet');
    const send = screen.getAllByRole('button').find(b => b.querySelector('.lucide-send'));
    await user.click(send!);

    await waitFor(() => {
      expect(mockEdit3D).toHaveBeenCalledTimes(1);
    });
    expect(mockTextTo3D).not.toHaveBeenCalled();
    expect(mockImageTo3D).not.toHaveBeenCalled();
    expect(mockEdit3D).toHaveBeenCalledWith(expect.objectContaining({
      file_path: '/storage/outputs/existing.stl', prompt: 'add fillet'
    }));
  });

  it('Regression — synchronous completion bypasses SSE', async () => {
    const store = makeStore3D({ attachments: [] });
    mockApiClientPost.mockImplementation(async (url: string) => {
      if (url === '/generation/intent') {
        return { data: { intent: 'generate_3d', reply_text: '', prompt_payload: 'a gear', status: 'ok' } };
      }
      throw new Error(`Unexpected POST: ${url}`);
    });
    mockTextTo3D.mockResolvedValue(COMPLETED_JOB_3D);

    render(<AIAssistantSidebar />);
    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText(/Describe.*3D/i), 'a gear');
    const send = screen.getAllByRole('button').find(b => b.querySelector('.lucide-send'));
    await user.click(send!);

    await waitFor(() => {
      const setGenCalls = (store.setGenerating as ReturnType<typeof vi.fn>).mock.calls;
      const completedCall = setGenCalls.find(([isGen]) => isGen === false);
      expect(completedCall).toBeDefined();
    });
    expect(mockStreamJobProgress).not.toHaveBeenCalled();
    expect(store.setActiveFile).toHaveBeenCalledWith('/storage/outputs/test.stl');
  });
});
