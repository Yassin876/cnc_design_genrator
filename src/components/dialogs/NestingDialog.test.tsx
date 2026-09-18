import { vi } from 'vitest';

// Mock stores using the exact relative paths the component uses
vi.mock('../../app/store/useWorkspaceStore', () => ({
  useWorkspaceStore: vi.fn(),
}));

vi.mock('../../app/store/use2DWorkspaceStore', () => ({
  use2DWorkspaceStore: vi.fn(),
}));

vi.mock('../../services/cad/cadService', () => ({
  cadService: {
    runNesting: vi.fn().mockResolvedValue({
      parts_placed: 2,
      sheets_used: 1,
      material_efficiency: 85.5,
      placements: [],
    }),
  },
}));

import { render, screen } from '@testing-library/react';
import { useWorkspaceStore } from '../../app/store/useWorkspaceStore';
import { use2DWorkspaceStore } from '../../app/store/use2DWorkspaceStore';
import { NestingDialog } from './NestingDialog';

describe('NestingDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock useWorkspaceStore
    vi.mocked(useWorkspaceStore).mockReturnValue({
      isNestingModalOpen: true,
      setNestingModalOpen: vi.fn(),
      dxfContent: null,
      activeFilePath: null,
      activeFileName: null,
      loadFile: vi.fn(),
    } as any);

    // Mock use2DWorkspaceStore — nesting reads the current 2D DXF from here
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      dxfEntities: [],
      activeFilePath: '/path/to/part.dxf',
      activeFileName: 'test-part.dxf',
      setActiveFile: vi.fn(),
    } as any);
  });

  it('renders the dialog with Nest Parts Configuration title', () => {
    render(<NestingDialog />);
    
    expect(screen.getByText('Nest Parts Configuration')).toBeInTheDocument();
  });

  it('Parts Priorities tab lists parts from current workspace', () => {
    render(<NestingDialog />);
    
    // Should show the part from the mocked workspace
    expect(screen.getByText('test-part.dxf')).toBeInTheDocument();
  });

  it('renders Nest Parts button', () => {
    render(<NestingDialog />);
    
    expect(screen.getByText('Nest Parts')).toBeInTheDocument();
  });

  it('renders Cancel button', () => {
    render(<NestingDialog />);
    
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });
});
