import { describe, it, expect, beforeEach } from 'vitest';
import { use3DWorkspaceStore } from './use3DWorkspaceStore';

describe('use3DWorkspaceStore - 3D Multi-Part & Workspace State', () => {
  beforeEach(() => {
    use3DWorkspaceStore.getState().resetWorkspace();
  });

  it('initializes with default single body part', () => {
    const state = use3DWorkspaceStore.getState();
    expect(state.parts.length).toBe(1);
    expect(state.parts[0].id).toBe('part-main');
    expect(state.selectedNodeId).toBe('part-main');
    expect(state.assemblyMode).toBe(false);
  });

  it('associates activeFilePath with the active part on setActiveFile', () => {
    use3DWorkspaceStore.getState().setActiveFile('storage/outputs/model.stl');
    const state = use3DWorkspaceStore.getState();
    expect(state.activeFilePath).toBe('storage/outputs/model.stl');
    expect(state.activeFileName).toBe('model.stl');
    expect(state.parts[0].filePath).toBe('storage/outputs/model.stl');
    expect(state.parts[0].name).toBe('model.stl');
  });

  it('adds new parts with distinct IDs and offset coordinates', () => {
    use3DWorkspaceStore.getState().setActiveFile('storage/outputs/base.stl');
    use3DWorkspaceStore.getState().addNewPart('Chair Leg 1');

    const state = use3DWorkspaceStore.getState();
    expect(state.parts.length).toBe(2);
    expect(state.parts[1].name).toBe('Chair Leg 1');
    expect(state.selectedNodeId).toBe(state.parts[1].id);
    expect(state.treeNodes.length).toBe(2);
    expect(state.treeNodes[1].name).toBe('Chair Leg 1');

    // Add another part
    use3DWorkspaceStore.getState().addNewPart('Chair Leg 2');
    const state2 = use3DWorkspaceStore.getState();
    expect(state2.parts.length).toBe(3);
    expect(state2.parts[2].name).toBe('Chair Leg 2');
  });

  it('updates part dimensions and positions dynamically', () => {
    use3DWorkspaceStore.getState().addNewPart('Armrest');
    const newPartId = use3DWorkspaceStore.getState().selectedNodeId!;

    use3DWorkspaceStore.getState().updatePartDimensions(newPartId, { length: 80, width: 40, height: 20 });
    use3DWorkspaceStore.getState().updatePartPosition(newPartId, { x: 50, y: 10, z: 30 });

    const state = use3DWorkspaceStore.getState();
    const updated = state.parts.find(p => p.id === newPartId);
    expect(updated?.dimensions).toEqual({ length: 80, width: 40, height: 20 });
    expect(updated?.position).toEqual({ x: 50, y: 10, z: 30 });
  });

  it('toggles visibility and assemblyMode correctly', () => {
    const state = use3DWorkspaceStore.getState();
    const mainId = state.parts[0].id;

    use3DWorkspaceStore.getState().togglePartVisibility(mainId);
    expect(use3DWorkspaceStore.getState().parts[0].visible).toBe(false);

    use3DWorkspaceStore.getState().toggleAssemblyMode();
    expect(use3DWorkspaceStore.getState().assemblyMode).toBe(true);

    use3DWorkspaceStore.getState().toggleAssemblyMode();
    expect(use3DWorkspaceStore.getState().assemblyMode).toBe(false);
  });

  it('supports undo and redo for part creation', () => {
    use3DWorkspaceStore.getState().addNewPart('Test Part');
    expect(use3DWorkspaceStore.getState().parts.length).toBe(2);

    use3DWorkspaceStore.getState().undo();
    expect(use3DWorkspaceStore.getState().parts.length).toBe(1);

    use3DWorkspaceStore.getState().redo();
    expect(use3DWorkspaceStore.getState().parts.length).toBe(2);
  });
});
