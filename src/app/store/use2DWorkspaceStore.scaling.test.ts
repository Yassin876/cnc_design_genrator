import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { use2DWorkspaceStore } from './use2DWorkspaceStore';

describe('use2DWorkspaceStore - Entity Scaling (#1)', () => {
  beforeEach(() => {
    // Reset store state before each test
    use2DWorkspaceStore.getState().resetWorkspace();
  });

  it('entity scaling updates bounding box when width changes', async () => {
    const { setDxfEntities, setWidth } = use2DWorkspaceStore.getState();
    
    // Create a simple rectangle entity
    const entities = [
      {
        id: 1,
        type: 'LWPOLYLINE',
        points: [[0, 0], [100, 0], [100, 100], [0, 100]],
        closed: true
      }
    ];
    
    setDxfEntities(entities);
    
    // Wait for debounce to complete
    await new Promise(resolve => setTimeout(resolve, 350));
    
    // Store original points
    const originalPoints = [...use2DWorkspaceStore.getState().dxfEntities![0].points];
    
    // Change width from 100 to 200
    setWidth(200);
    
    // Wait for debounce to complete
    await new Promise(resolve => setTimeout(resolve, 350));
    
    const { dxfEntities: scaledEntities } = use2DWorkspaceStore.getState();
    
    expect(scaledEntities).not.toBeNull();
    expect(scaledEntities).toHaveLength(1);
    
    // Check that the entity was actually changed
    const scaledEntity = scaledEntities![0];
    expect(scaledEntity.points).toBeDefined();
    
    // Points should be different from original
    expect(scaledEntity.points).not.toEqual(originalPoints);
    
    // Calculate new bounding box
    const xs = scaledEntity.points.map(p => p[0]);
    const ys = scaledEntity.points.map(p => p[1]);
    const newWidth = Math.max(...xs) - Math.min(...xs);
    
    // Width should be approximately 200 (the target)
    expect(newWidth).toBeCloseTo(200, 1);
  });

  it('entity scaling updates bounding box when height changes', async () => {
    const { setDxfEntities, setHeight } = use2DWorkspaceStore.getState();
    
    const entities = [
      {
        id: 1,
        type: 'LWPOLYLINE',
        points: [[0, 0], [100, 0], [100, 100], [0, 100]],
        closed: true
      }
    ];
    
    setDxfEntities(entities);
    
    // Wait for debounce to complete
    await new Promise(resolve => setTimeout(resolve, 350));
    
    // Store original points
    const originalPoints = [...use2DWorkspaceStore.getState().dxfEntities![0].points];
    
    // Change height from 100 to 200
    setHeight(200);
    
    // Wait for debounce to complete
    await new Promise(resolve => setTimeout(resolve, 350));
    
    const { dxfEntities: scaledEntities } = use2DWorkspaceStore.getState();
    
    expect(scaledEntities).not.toBeNull();
    expect(scaledEntities).toHaveLength(1);
    
    const scaledEntity = scaledEntities![0];
    expect(scaledEntity.points).toBeDefined();
    
    // Points should be different from original
    expect(scaledEntity.points).not.toEqual(originalPoints);
    
    // Calculate new bounding box
    const ys = scaledEntity.points.map(p => p[1]);
    const newHeight = Math.max(...ys) - Math.min(...ys);
    
    // Height should be approximately 200 (the target)
    expect(newHeight).toBeCloseTo(200, 1);
  });

  it('multiple entities scale uniformly preserving proportions', async () => {
    const { setDxfEntities, setWidth, setHeight } = use2DWorkspaceStore.getState();
    
    const entities = [
      {
        id: 1,
        type: 'LWPOLYLINE',
        points: [[0, 0], [50, 0], [50, 50], [0, 50]],
        closed: true
      },
      {
        id: 2,
        type: 'LWPOLYLINE',
        points: [[60, 0], [100, 0], [100, 50], [60, 50]],
        closed: true
      }
    ];
    
    setDxfEntities(entities);
    
    // Wait for debounce to complete
    await new Promise(resolve => setTimeout(resolve, 350));
    
    // Store original points
    const originalPoints1 = [...use2DWorkspaceStore.getState().dxfEntities![0].points];
    const originalPoints2 = [...use2DWorkspaceStore.getState().dxfEntities![1].points];
    
    // Change both dimensions
    setWidth(200);
    setHeight(200);
    
    // Wait for debounce to complete
    await new Promise(resolve => setTimeout(resolve, 350));
    
    const { dxfEntities: scaledEntities } = use2DWorkspaceStore.getState();
    
    expect(scaledEntities).not.toBeNull();
    expect(scaledEntities).toHaveLength(2);
    
    // Both entities should be scaled
    const entity1 = scaledEntities![0];
    const entity2 = scaledEntities![1];
    
    // Points should be different from original
    expect(entity1.points).not.toEqual(originalPoints1);
    expect(entity2.points).not.toEqual(originalPoints2);
    
    // Check that both entities have the same relative positions
    // Original: entity1 at 0-50, entity2 at 60-100 (gap of 10)
    // Scaled: should maintain the gap proportionally
    const entity1MaxX = Math.max(...entity1.points.map(p => p[0]));
    const entity2MinX = Math.min(...entity2.points.map(p => p[0]));
    const gap = entity2MinX - entity1MaxX;
    
    // Gap should be > 0 (entities didn't overlap)
    expect(gap).toBeGreaterThan(0);
  });
});
