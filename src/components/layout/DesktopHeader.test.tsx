import { vi } from 'vitest';

vi.mock('../../app/store/useWorkspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}));

vi.mock('../../app/store/use2DWorkspaceStore', () => ({
  use2DWorkspaceStore: vi.fn(),
}));

vi.mock('../../app/store/use3DWorkspaceStore', () => ({
  use3DWorkspaceStore: vi.fn(),
}));

vi.mock('../../app/store/useAuthStore', () => ({
  useAuthStore: vi.fn(),
}));

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { use2DWorkspaceStore } from '../../app/store/use2DWorkspaceStore';
import { use3DWorkspaceStore } from '../../app/store/use3DWorkspaceStore';
import { useAuthStore } from '../../app/store/useAuthStore';
import { DesktopHeader } from './DesktopHeader';

describe('DesktopHeader - Undo/Redo Buttons (#6)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    vi.mocked(useAuthStore).mockReturnValue({
      user: { id: 'test_user' },
    } as any);
  });

  it('Undo button is disabled when 2D canUndo is false', () => {
    vi.mocked(useWorkspaceStore).mockReturnValue({
      viewMode: 'workspace_2d',
      setExportModalOpen: vi.fn(),
      loadDXFContent: vi.fn(),
    } as any);

    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      canUndo: vi.fn(() => false),
      undo: vi.fn(),
    } as any);

    vi.mocked(use3DWorkspaceStore).mockReturnValue({
      canUndo: vi.fn(() => false),
      undo: vi.fn(),
    } as any);

    render(<DesktopHeader />);
    
    const undoButton = screen.getByTestId('undo-button');
    expect(undoButton).toBeInTheDocument();
    expect(undoButton).toBeDisabled();
  });

  it('Undo button is enabled when 2D canUndo is true', () => {
    vi.mocked(useWorkspaceStore).mockReturnValue({
      viewMode: 'workspace_2d',
      setExportModalOpen: vi.fn(),
      loadDXFContent: vi.fn(),
    } as any);

    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      canUndo: vi.fn(() => true),
      undo: vi.fn(),
    } as any);

    vi.mocked(use3DWorkspaceStore).mockReturnValue({
      canUndo: vi.fn(() => false),
      undo: vi.fn(),
    } as any);

    render(<DesktopHeader />);
    
    const undoButton = screen.getByTestId('undo-button');
    expect(undoButton).toBeInTheDocument();
    expect(undoButton).not.toBeDisabled();
  });

  it('Undo button calls store undo action on click in 2D mode', async () => {
    const mockUndo = vi.fn();
    vi.mocked(useWorkspaceStore).mockReturnValue({
      viewMode: 'workspace_2d',
      setExportModalOpen: vi.fn(),
      loadDXFContent: vi.fn(),
    } as any);

    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      canUndo: vi.fn(() => true),
      undo: mockUndo,
    } as any);

    vi.mocked(use3DWorkspaceStore).mockReturnValue({
      canUndo: vi.fn(() => false),
      undo: vi.fn(),
    } as any);

    const user = userEvent.setup();
    render(<DesktopHeader />);
    
    const undoButton = screen.getByTestId('undo-button');
    await user.click(undoButton);
    
    expect(mockUndo).toHaveBeenCalled();
  });

  it('Redo button is always disabled (not implemented yet)', () => {
    vi.mocked(useWorkspaceStore).mockReturnValue({
      viewMode: 'workspace_2d',
      setExportModalOpen: vi.fn(),
      loadDXFContent: vi.fn(),
    } as any);

    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      canUndo: vi.fn(() => true),
      undo: vi.fn(),
    } as any);

    vi.mocked(use3DWorkspaceStore).mockReturnValue({
      canUndo: vi.fn(() => false),
      undo: vi.fn(),
    } as any);

    render(<DesktopHeader />);
    
    const redoButton = screen.getByTestId('redo-button');
    expect(redoButton).toBeInTheDocument();
    expect(redoButton).toBeDisabled();
  });
});
