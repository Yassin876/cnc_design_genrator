import { vi } from 'vitest';

// Mock stores using the exact relative paths the component uses
vi.mock('../../../app/store/use2DWorkspaceStore', () => ({
  use2DWorkspaceStore: vi.fn(),
}));

vi.mock('../../../app/store/useWorkspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}));

vi.mock('../../../services/cad/cadService', () => ({
  cadService: {
    parseDXF: vi.fn(),
    parseDXFContent: vi.fn(),
  },
}));

// Mock HTMLCanvasElement context
HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
  fillRect: vi.fn(),
  clearRect: vi.fn(),
  getImageData: vi.fn(),
  putImageData: vi.fn(),
  createImageData: vi.fn(),
  setTransform: vi.fn(),
  resetTransform: vi.fn(),
  save: vi.fn(),
  restore: vi.fn(),
  beginPath: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  closePath: vi.fn(),
  stroke: vi.fn(),
  translate: vi.fn(),
  scale: vi.fn(),
  rotate: vi.fn(),
  arc: vi.fn(),
  fill: vi.fn(),
  measureText: vi.fn(() => ({ width: 0 })),
  transform: vi.fn(),
  rect: vi.fn(),
  clip: vi.fn(),
  fillText: vi.fn(),
  strokeText: vi.fn(),
  font: '10px sans-serif',
  textAlign: 'left',
  textBaseline: 'top',
} as any));

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { use2DWorkspaceStore } from '../../../app/store/use2DWorkspaceStore';
import { useWorkspaceStore } from '../../../app/store/useWorkspaceStore';
import { Canvas2D } from './Canvas2D';

describe('Canvas2D - Toolbar Sizing (#2)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      activeFilePath: null,
      dxfEntities: [],
      setDxfEntities: vi.fn(),
      activeView: '2d',
      setActiveView: vi.fn(),
      width: 100,
      height: 100,
      markDirty: vi.fn(),
      undo: vi.fn(),
      canUndo: vi.fn(() => false),
    } as any);

    vi.mocked(useWorkspaceStore).mockReturnValue({
      dxfContent: null,
      setDxfContent: vi.fn(),
      setNestingModalOpen: vi.fn(),
    } as any);
  });

  it('all toolbar buttons are present', () => {
    render(<Canvas2D />);
    
    // Check that toolbar buttons exist
    expect(screen.getByTitle('Select Tool')).toBeInTheDocument();
    expect(screen.getByTitle('Line Tool')).toBeInTheDocument();
    expect(screen.getByTitle('Rectangle Tool')).toBeInTheDocument();
    expect(screen.getByTitle('Circle Tool')).toBeInTheDocument();
    expect(screen.getByTitle('Toggle Coordinate Rulers')).toBeInTheDocument();
    expect(screen.getByTitle('Auto Dimensions')).toBeInTheDocument();
    expect(screen.getByTitle('Nest Parts')).toBeInTheDocument();
    expect(screen.getByTitle('Undo (Ctrl+Z)')).toBeInTheDocument();
    expect(screen.getByTitle('Zoom In')).toBeInTheDocument();
    expect(screen.getByTitle('Zoom Out')).toBeInTheDocument();
    expect(screen.getByTitle('Fit to View')).toBeInTheDocument();
    expect(screen.getByTitle('Toggle Fullscreen')).toBeInTheDocument();
  });
});

describe('Canvas2D - View Selector (#5)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock use2DWorkspaceStore
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      activeFilePath: null,
      dxfEntities: [],
      setDxfEntities: vi.fn(),
      activeView: '2d',
      setActiveView: vi.fn(),
      width: 100,
      height: 100,
      markDirty: vi.fn(),
      undo: vi.fn(),
      canUndo: vi.fn(() => false),
    } as any);

    // Mock useWorkspaceStore
    vi.mocked(useWorkspaceStore).mockReturnValue({
      dxfContent: null,
      setDxfContent: vi.fn(),
      setNestingModalOpen: vi.fn(),
    } as any);
  });

  it('all three view options are present in the DOM without Isometric', () => {
    render(<Canvas2D />);
    
    expect(screen.getByText('Front')).toBeInTheDocument();
    expect(screen.getByText('Top')).toBeInTheDocument();
    expect(screen.getByText('Right')).toBeInTheDocument();
    expect(screen.queryByText('Isometric')).not.toBeInTheDocument();
  });
});

describe('Canvas2D - Nest Parts Button (#6)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock use2DWorkspaceStore
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      activeFilePath: null,
      dxfEntities: [],
      setDxfEntities: vi.fn(),
      activeView: '2d',
      setActiveView: vi.fn(),
      width: 100,
      height: 100,
      markDirty: vi.fn(),
      undo: vi.fn(),
      canUndo: vi.fn(() => false),
    } as any);

    // Mock useWorkspaceStore
    vi.mocked(useWorkspaceStore).mockReturnValue({
      dxfContent: null,
      setDxfContent: vi.fn(),
      setNestingModalOpen: vi.fn(),
    } as any);
  });

  it('Nest Parts button is present and opens the modal on click', async () => {
    const setNestingModalOpen = vi.fn();
    vi.mocked(useWorkspaceStore).mockReturnValue({
      dxfContent: null,
      setDxfContent: vi.fn(),
      setNestingModalOpen: setNestingModalOpen,
    } as any);
    
    const user = userEvent.setup();
    render(<Canvas2D />);
    
    // Find the Nest button
    const nestButton = screen.getByText('Nest');
    expect(nestButton).toBeInTheDocument();
    
    // Click the button
    await user.click(nestButton);
    
    // Verify setNestingModalOpen was called with true
    expect(setNestingModalOpen).toHaveBeenCalledWith(true);
  });

  it('Undo button is disabled when canUndo is false', () => {
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      activeFilePath: null,
      dxfEntities: [],
      setDxfEntities: vi.fn(),
      activeView: '2d',
      setActiveView: vi.fn(),
      width: 100,
      height: 100,
      markDirty: vi.fn(),
      undo: vi.fn(),
      canUndo: vi.fn(() => false),
    } as any);

    vi.mocked(useWorkspaceStore).mockReturnValue({
      dxfContent: null,
      setDxfContent: vi.fn(),
      setNestingModalOpen: vi.fn(),
    } as any);

    render(<Canvas2D />);
    
    // Find the actual button element, not the span
    const undoButton = screen.getByText('Undo').closest('button');
    expect(undoButton).toBeInTheDocument();
    expect(undoButton).toBeDisabled();
  });

  it('Undo button is enabled when canUndo is true', () => {
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      activeFilePath: null,
      dxfEntities: [],
      setDxfEntities: vi.fn(),
      activeView: '2d',
      setActiveView: vi.fn(),
      width: 100,
      height: 100,
      markDirty: vi.fn(),
      undo: vi.fn(),
      canUndo: vi.fn(() => true),
    } as any);

    vi.mocked(useWorkspaceStore).mockReturnValue({
      dxfContent: null,
      setDxfContent: vi.fn(),
      setNestingModalOpen: vi.fn(),
    } as any);

    render(<Canvas2D />);
    
    const undoButton = screen.getByText('Undo').closest('button');
    expect(undoButton).toBeInTheDocument();
    expect(undoButton).not.toBeDisabled();
  });

  it('Undo button calls store undo action on click', async () => {
    const mockUndo = vi.fn();
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      activeFilePath: null,
      dxfEntities: [],
      setDxfEntities: vi.fn(),
      activeView: '2d',
      setActiveView: vi.fn(),
      width: 100,
      height: 100,
      markDirty: vi.fn(),
      undo: mockUndo,
      canUndo: vi.fn(() => true),
    } as any);

    vi.mocked(useWorkspaceStore).mockReturnValue({
      dxfContent: null,
      setDxfContent: vi.fn(),
      setNestingModalOpen: vi.fn(),
    } as any);

    const user = userEvent.setup();
    render(<Canvas2D />);
    
    const undoButton = screen.getByText('Undo').closest('button');
    await user.click(undoButton!);
    
    expect(mockUndo).toHaveBeenCalled();
  });
});
