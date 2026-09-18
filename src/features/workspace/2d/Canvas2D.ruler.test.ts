import { describe, it, expect } from 'vitest';
import { getRulerValue } from './Canvas2D';

describe('Canvas2D - Ruler Value Calculation (#4)', () => {
  it('test_ruler_value_changes_with_pan', () => {
    const pixelPos = 100;
    const zoomScale = 2.0;
    
    const value1 = getRulerValue(pixelPos, 0, zoomScale);
    const value2 = getRulerValue(pixelPos, 50, zoomScale);
    
    expect(value1).toBe(50);
    expect(value2).toBe(25);
    expect(value1).not.toBe(value2);
  });

  it('test_ruler_value_changes_with_zoom', () => {
    const pixelPos = 100;
    const panOffset = 0;
    
    const value1 = getRulerValue(pixelPos, panOffset, 1.0);
    const value2 = getRulerValue(pixelPos, panOffset, 2.0);
    
    expect(value1).toBe(100);
    expect(value2).toBe(50);
    expect(value1).not.toBe(value2);
  });

  it('test_ruler_value_formula', () => {
    // Test the actual formula: (pixelPos - panOffset) / zoomScale
    const pixelPos = 200;
    const panOffset = 50;
    const zoomScale = 2.0;
    
    const value = getRulerValue(pixelPos, panOffset, zoomScale);
    
    // Expected: (200 - 50) / 2 = 75
    expect(value).toBe(75);
  });

  it('test_ruler_value_with_negative_pan', () => {
    const pixelPos = 100;
    const panOffset = -50;
    const zoomScale = 2.0;
    
    const value = getRulerValue(pixelPos, panOffset, zoomScale);
    
    // Expected: (100 - (-50)) / 2 = 75
    expect(value).toBe(75);
  });

  it('test_ruler_value_with_fractional_zoom', () => {
    const pixelPos = 100;
    const panOffset = 0;
    const zoomScale = 0.5;
    
    const value = getRulerValue(pixelPos, panOffset, zoomScale);
    
    // Expected: (100 - 0) / 0.5 = 200
    expect(value).toBe(200);
  });
});
