import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { PropertiesInspector } from './PropertiesInspector';
import { useWorkspaceStore } from '../../../app/store/useWorkspaceStore';
import { use2DWorkspaceStore } from '../../../app/store/use2DWorkspaceStore';
import { use3DWorkspaceStore } from '../../../app/store/use3DWorkspaceStore';

vi.mock('../../../app/store/useWorkspaceStore');
vi.mock('../../../app/store/use2DWorkspaceStore');
vi.mock('../../../app/store/use3DWorkspaceStore');

describe('PropertiesInspector - 2D Mode', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (useWorkspaceStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      viewMode: 'workspace_2d',
    });

    (use2DWorkspaceStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      width: 500,
      height: 300,
      toolDiameter: 3.175,
      setWidth: vi.fn(),
      setHeight: vi.fn(),
      setToolDiameter: vi.fn(),
      inputErrors: {},
      validateInputs: vi.fn(),
      dxfEntities: [],
    });
  });

  it('renders 2D Dimensions title and inputs', () => {
    render(<PropertiesInspector />);

    expect(screen.getByText('2D Properties Inspector')).toBeInTheDocument();
    expect(screen.getByText('2D Dimensions')).toBeInTheDocument();
    expect(screen.getByText(/Width \(X\)/)).toBeInTheDocument();
    expect(screen.getByText(/Height \(Y\)/)).toBeInTheDocument();
    expect(screen.getByText('Tool Diameter')).toBeInTheDocument();
  });

  it('Geometry Metrics section is completely removed', () => {
    render(<PropertiesInspector />);

    expect(screen.queryByText('Geometry Metrics')).not.toBeInTheDocument();
    expect(screen.queryByText('Vector Entities')).not.toBeInTheDocument();
    expect(screen.queryByText('Specification')).not.toBeInTheDocument();
  });

  it('Boundary Summary with reactive Total Perimeter is present', () => {
    render(<PropertiesInspector />);

    expect(screen.getByText('Boundary Summary')).toBeInTheDocument();
    expect(screen.getByText('Total Perimeter')).toBeInTheDocument();
    expect(screen.getByTestId('total-perimeter-value')).toBeInTheDocument();
  });
});

describe('PropertiesInspector - 3D Mode', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (useWorkspaceStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      viewMode: 'workspace_3d',
    });

    (use3DWorkspaceStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      length: 100,
      width: 100,
      height: 50,
      setLength: vi.fn(),
      setWidth: vi.fn(),
      setHeight: vi.fn(),
      parts: [
        {
          id: 'part-1',
          name: 'Main Body',
          visible: true,
          isAssembled: true,
          dimensions: { length: 100, width: 100, height: 50 },
          position: { x: 0, y: 0, z: 0 },
          color: '#6366f1'
        }
      ],
      treeNodes: [{ id: 'part-1', name: 'Main Body', type: 'Body', visible: true }],
      selectedNodeId: 'part-1',
      selectNode: vi.fn(),
      togglePartVisibility: vi.fn(),
      removePart: vi.fn(),
      renamePart: vi.fn(),
      addNewPart: vi.fn(),
      updatePartDimensions: vi.fn(),
      updatePartPosition: vi.fn(),
      assemblyMode: false,
      toggleAssemblyMode: vi.fn(),
      inputErrors: {},
    } as any);
  });

  it('3D inspector position transform is completely removed', () => {
    render(<PropertiesInspector />);
    
    expect(screen.queryByText('Position Transform')).not.toBeInTheDocument();
  });

  it('3D inspector renders bounding dimensions', () => {
    render(<PropertiesInspector />);
    
    expect(screen.getByText('Main Body Dimensions')).toBeInTheDocument();
    expect(screen.getByText(/Length \(L\)/)).toBeInTheDocument();
    expect(screen.getByText(/Width \(W\)/)).toBeInTheDocument();
    expect(screen.getByText(/Height \(H\)/)).toBeInTheDocument();
  });

  it('3D inspector material selection is completely removed', () => {
    render(<PropertiesInspector />);
    
    expect(screen.queryByText('Stock Material Selection')).not.toBeInTheDocument();
    expect(screen.queryByText('Material Stock')).not.toBeInTheDocument();
  });

  it('3D inspector renders Model Tree tab toggle', () => {
    render(<PropertiesInspector />);
    
    expect(screen.getByText(/Model Tree/)).toBeInTheDocument();
  });
});
