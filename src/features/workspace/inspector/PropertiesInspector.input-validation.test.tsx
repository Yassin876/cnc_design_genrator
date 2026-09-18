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

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useWorkspaceStore } from '../../../app/store/useWorkspaceStore';
import { use2DWorkspaceStore } from '../../../app/store/use2DWorkspaceStore';
import { PropertiesInspector } from './PropertiesInspector';

describe('PropertiesInspector - Input Validation (#1, #2)', () => {
  const mockSetWidth = vi.fn();
  const mockSetHeight = vi.fn();
  const mockSetToolDiameter = vi.fn();
  const mockValidateInputs = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    
    vi.mocked(useWorkspaceStore).mockReturnValue({
      viewMode: 'workspace_2d',
    } as any);
    
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      width: 100,
      height: 100,
      toolDiameter: 5,
      setWidth: mockSetWidth,
      setHeight: mockSetHeight,
      setToolDiameter: mockSetToolDiameter,
      inputErrors: {},
      dxfEntities: [],
      validateInputs: mockValidateInputs,
      undo: vi.fn(),
      canUndo: vi.fn(() => false),
    } as any);
  });

  it('Width input change calls setWidth and validateInputs', async () => {
    const user = userEvent.setup();
    render(<PropertiesInspector />);
    
    const widthInput = screen.getByTestId('width-input');
    await user.clear(widthInput);
    await user.type(widthInput, '200');
    
    expect(mockSetWidth).toHaveBeenCalled();
    expect(mockSetWidth).toHaveBeenCalledWith(expect.any(Number));
    expect(mockValidateInputs).toHaveBeenCalled();
  });

  it('Height input change calls setHeight and validateInputs', async () => {
    const user = userEvent.setup();
    render(<PropertiesInspector />);
    
    const heightInput = screen.getByTestId('height-input');
    await user.clear(heightInput);
    await user.type(heightInput, '150');
    
    expect(mockSetHeight).toHaveBeenCalled();
    expect(mockSetHeight).toHaveBeenCalledWith(expect.any(Number));
    expect(mockValidateInputs).toHaveBeenCalled();
  });

  it('Tool Diameter input change calls setToolDiameter and validateInputs', async () => {
    const user = userEvent.setup();
    render(<PropertiesInspector />);
    
    const toolDiameterInput = screen.getByTestId('tool-diameter-input');
    await user.clear(toolDiameterInput);
    await user.type(toolDiameterInput, '10');
    
    expect(mockSetToolDiameter).toHaveBeenCalled();
    expect(mockSetToolDiameter).toHaveBeenCalledWith(expect.any(Number));
    expect(mockValidateInputs).toHaveBeenCalled();
  });

  it('Total Perimeter updates when width/height change', async () => {
    const user = userEvent.setup();
    
    // Initial perimeter: (100 + 100) * 2 = 400
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      width: 100,
      height: 100,
      toolDiameter: 5,
      setWidth: mockSetWidth,
      setHeight: mockSetHeight,
      setToolDiameter: mockSetToolDiameter,
      inputErrors: {},
      dxfEntities: [],
      validateInputs: mockValidateInputs,
      undo: vi.fn(),
      canUndo: vi.fn(() => false),
    } as any);
    
    const { rerender } = render(<PropertiesInspector />);
    expect(screen.getByTestId('total-perimeter')).toHaveTextContent('400.0');
    
    // Change width to 200: (200 + 100) * 2 = 600
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      width: 200,
      height: 100,
      toolDiameter: 5,
      setWidth: mockSetWidth,
      setHeight: mockSetHeight,
      setToolDiameter: mockSetToolDiameter,
      inputErrors: {},
      dxfEntities: [],
      validateInputs: mockValidateInputs,
      undo: vi.fn(),
      canUndo: vi.fn(() => false),
    } as any);
    
    rerender(<PropertiesInspector />);
    expect(screen.getByTestId('total-perimeter')).toHaveTextContent('600.0');
  });

  it('shows error message when width has validation error', () => {
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      width: 0,
      height: 100,
      toolDiameter: 5,
      setWidth: mockSetWidth,
      setHeight: mockSetHeight,
      setToolDiameter: mockSetToolDiameter,
      inputErrors: { width: 'Width (X) is required and must be > 0' },
      dxfEntities: [],
      validateInputs: mockValidateInputs,
      undo: vi.fn(),
      canUndo: vi.fn(() => false),
    } as any);
    
    render(<PropertiesInspector />);
    
    expect(screen.getByText('Width (X) is required and must be > 0')).toBeInTheDocument();
  });

  it('shows error message when height has validation error', () => {
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      width: 100,
      height: 0,
      toolDiameter: 5,
      setWidth: mockSetWidth,
      setHeight: mockSetHeight,
      setToolDiameter: mockSetToolDiameter,
      inputErrors: { height: 'Height (Y) is required and must be > 0' },
      dxfEntities: [],
      validateInputs: mockValidateInputs,
      undo: vi.fn(),
      canUndo: vi.fn(() => false),
    } as any);
    
    render(<PropertiesInspector />);
    
    expect(screen.getByText('Height (Y) is required and must be > 0')).toBeInTheDocument();
  });

  it('shows error message when tool diameter has validation error', () => {
    vi.mocked(use2DWorkspaceStore).mockReturnValue({
      width: 100,
      height: 100,
      toolDiameter: 0,
      setWidth: mockSetWidth,
      setHeight: mockSetHeight,
      setToolDiameter: mockSetToolDiameter,
      inputErrors: { toolDiameter: 'Tool Diameter is required and must be > 0' },
      dxfEntities: [],
      validateInputs: mockValidateInputs,
      undo: vi.fn(),
      canUndo: vi.fn(() => false),
    } as any);
    
    render(<PropertiesInspector />);
    
    expect(screen.getByText('Tool Diameter is required and must be > 0')).toBeInTheDocument();
  });
});
