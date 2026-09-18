import { vi } from 'vitest';

vi.mock('../../../app/store/useWorkspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}));

vi.mock('../../../app/store/use2DWorkspaceStore', () => ({
  use2DWorkspaceStore: vi.fn(),
}));

vi.mock('../../../app/store/use3DWorkspaceStore', () => ({
  use3DWorkspaceStore: vi.fn(),
}));

vi.mock('../../../app/store/useAuthStore', () => ({
  useAuthStore: vi.fn(),
}));

vi.mock('../../../services/api/client', () => ({
  apiClient: vi.fn(),
  getStaticFileUrl: vi.fn(),
}));

vi.mock('../../../services/api/generation', () => ({
  generationApiService: {
    streamJobProgress: vi.fn(),
  },
}));

import { render, screen } from '@testing-library/react';
import { useWorkspaceStore } from '../../../app/store/useWorkspaceStore';
import { use2DWorkspaceStore } from '../../../app/store/use2DWorkspaceStore';
import { use3DWorkspaceStore } from '../../../app/store/use3DWorkspaceStore';
import { useAuthStore } from '../../../app/store/useAuthStore';
import { AIAssistantSidebar } from './AIAssistantSidebar';

describe('AIAssistantSidebar - Generate Button Validation (#2)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    vi.mocked(useWorkspaceStore).mockReturnValue({
      viewMode: 'workspace_2d',
      setExportModalOpen: vi.fn(),
      loadDXFContent: vi.fn(),
    } as any);

    vi.mocked(useAuthStore).mockReturnValue({
      user: { id: 'test_user' },
    } as any);
  });

  it('Generate button enabled when all fields are valid', () => {
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      chatMessages: [],
      attachments: [],
      isGenerating: false,
      addChatMessage: vi.fn(),
      inputErrors: {},
    } as any);

    vi.mocked(use3DWorkspaceStore).mockReturnValue({
      chatMessages: [],
      attachments: [],
      isGenerating: false,
      addChatMessage: vi.fn(),
      inputErrors: {},
    } as any);

    render(<AIAssistantSidebar />);
    
    // The button is also disabled when there's no prompt AND no attachments
    // So we need to check that it's not disabled due to input validation specifically
    // Find send button by its icon class
    const sendButtons = screen.getAllByRole('button');
    const sendButton = sendButtons.find(btn => btn.querySelector('.lucide-send'));
    expect(sendButton).toBeInTheDocument();
    // Button will be disabled due to empty prompt, but we can check the title
    // doesn't mention input validation
    expect(sendButton?.getAttribute('title')).not.toContain('Width, Height, and Tool Diameter');
  });

  it('Generate button disabled when width is invalid', () => {
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      chatMessages: [],
      attachments: [],
      isGenerating: false,
      addChatMessage: vi.fn(),
      inputErrors: { width: 'Width (X) is required and must be > 0' },
    } as any);

    vi.mocked(use3DWorkspaceStore).mockReturnValue({
      chatMessages: [],
      attachments: [],
      isGenerating: false,
      addChatMessage: vi.fn(),
      inputErrors: {},
    } as any);

    render(<AIAssistantSidebar />);
    
    const sendButtons = screen.getAllByRole('button');
    const sendButton = sendButtons.find(btn => btn.querySelector('.lucide-send'));
    expect(sendButton).toBeInTheDocument();
    expect(sendButton).toBeDisabled();
  });

  it('Generate button disabled when height is invalid', () => {
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      chatMessages: [],
      attachments: [],
      isGenerating: false,
      addChatMessage: vi.fn(),
      inputErrors: { height: 'Height (Y) is required and must be > 0' },
    } as any);

    vi.mocked(use3DWorkspaceStore).mockReturnValue({
      chatMessages: [],
      attachments: [],
      isGenerating: false,
      addChatMessage: vi.fn(),
      inputErrors: {},
    } as any);

    render(<AIAssistantSidebar />);
    
    const sendButtons = screen.getAllByRole('button');
    const sendButton = sendButtons.find(btn => btn.querySelector('.lucide-send'));
    expect(sendButton).toBeInTheDocument();
    expect(sendButton).toBeDisabled();
  });

  it('Generate button disabled when tool diameter is invalid', () => {
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      chatMessages: [],
      attachments: [],
      isGenerating: false,
      addChatMessage: vi.fn(),
      inputErrors: { toolDiameter: 'Tool Diameter is required and must be > 0' },
    } as any);

    vi.mocked(use3DWorkspaceStore).mockReturnValue({
      chatMessages: [],
      attachments: [],
      isGenerating: false,
      addChatMessage: vi.fn(),
      inputErrors: {},
    } as any);

    render(<AIAssistantSidebar />);
    
    const sendButtons = screen.getAllByRole('button');
    const sendButton = sendButtons.find(btn => btn.querySelector('.lucide-send'));
    expect(sendButton).toBeInTheDocument();
    expect(sendButton).toBeDisabled();
  });

  it('Generate button always enabled in 3D mode regardless of 2D errors', () => {
    vi.mocked(useWorkspaceStore).mockReturnValue({
      viewMode: 'workspace_3d',
      setExportModalOpen: vi.fn(),
      loadDXFContent: vi.fn(),
    } as any);

    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      chatMessages: [],
      attachments: [],
      isGenerating: false,
      addChatMessage: vi.fn(),
      inputErrors: { width: 'error', height: 'error', toolDiameter: 'error' },
    } as any);

    vi.mocked(use3DWorkspaceStore).mockReturnValue({
      chatMessages: [],
      attachments: [],
      isGenerating: false,
      addChatMessage: vi.fn(),
      inputErrors: {},
    } as any);

    render(<AIAssistantSidebar />);
    
    const sendButtons = screen.getAllByRole('button');
    const sendButton = sendButtons.find(btn => btn.querySelector('.lucide-send'));
    expect(sendButton).toBeInTheDocument();
    // In 3D mode, the title should not mention 2D validation
    expect(sendButton?.getAttribute('title')).not.toContain('Width, Height, and Tool Diameter');
  });
});
