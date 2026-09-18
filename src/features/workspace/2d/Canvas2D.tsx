import React, { useEffect, useRef, useState } from 'react';
import { use2DWorkspaceStore } from '../../../app/store/use2DWorkspaceStore';
import { useWorkspaceStore } from '../../../app/store/useWorkspaceStore';
import { cadService } from '../../../services/cad/cadService';
import {
  ZoomIn, ZoomOut, Maximize, FileCode,
  PenTool, Circle as CircleIcon, Square, Slash, Ruler, Sparkles,
  Maximize2, Layers3, Undo
} from 'lucide-react';

// Ruler value calculation (exported for testing)
export const getRulerValue = (pixelPos: number, panOffset: number, zoomScale: number): number => {
  return (pixelPos - panOffset) / zoomScale;
};

export const Canvas2D: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const {
    activeFilePath,
    dxfEntities, setDxfEntities,
    activeView, setActiveView,
    width: sheetWidth, height: sheetHeight,
    markDirty,
    undo,
    canUndo
  } = use2DWorkspaceStore();

  const { dxfContent, setDxfContent, setNestingModalOpen } = useWorkspaceStore();

  // Local Viewport Transform
  const [scale, setScale] = useState(1.0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [startPan, setStartPan] = useState({ x: 0, y: 0 });

  // UI / Layer Visibility States
  const [showRulers, setShowRulers] = useState(true);
  const [showDimensions, setShowDimensions] = useState(true);
  const [layers, setLayers] = useState<{ OUTLINE: boolean; HOLES: boolean; CUTOUTS: boolean; ENGRAVE: boolean; SHEET_BORDER: boolean }>({
    OUTLINE: true,
    HOLES: true,
    CUTOUTS: true,
    ENGRAVE: true,
    SHEET_BORDER: true
  });

  // Active Tool state
  const [activeTool, setActiveTool] = useState<'select' | 'line' | 'rectangle' | 'circle'>('select');

  // Drawing State
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [drawCurrent, setDrawCurrent] = useState<{ x: number; y: number } | null>(null);

  // Loading state for DXF rendering
  const [loading, setLoading] = useState(false);

  // Resize canvas to container
  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;

      const rect = container.getBoundingClientRect();
      canvas.width = rect.width;
      canvas.height = rect.height;

      // Initial center pan if not panned yet
      if (pan.x === 0 && pan.y === 0) {
        setPan({ x: rect.width / 2, y: rect.height / 2 });
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Fetch / Parse DXF whenever active file path or dxfContent changes
  useEffect(() => {
    if (!activeFilePath && !dxfContent) {
      // Create empty sheet border if no file is open
      const halfW = (sheetWidth || 500) / 2;
      const halfH = (sheetHeight || 500) / 2;
      setDxfEntities([
        {
          type: 'LWPOLYLINE',
          layer: 'SHEET_BORDER',
          points: [
            [-halfW, -halfH],
            [halfW, -halfH],
            [halfW, halfH],
            [-halfW, halfH],
            [-halfW, -halfH]
          ],
          closed: true
        }
      ]);
      return;
    }

    if (activeFilePath) {
      setLoading(true);
      cadService.parseDXF(activeFilePath)
        .then((res) => {
          if (res) {
            const entities = Array.isArray(res.entities)
              ? res.entities
              : (Array.isArray(res.entities?.entities) ? res.entities.entities : (Array.isArray(res) ? res : []));
            if (entities.length > 0) {
              setDxfEntities(entities);
              setTimeout(() => handleFit(entities), 50);
            }
          }
        })
        .catch((err) => {
          console.error('Failed to load DXF entities:', err);
        })
        .finally(() => setLoading(false));
    }
  }, [activeFilePath, sheetWidth, sheetHeight]);

  // Handle in-memory DXF content (from Generate API)
  useEffect(() => {
    if (dxfContent) {
      setLoading(true);
      cadService.parseDXFContent(dxfContent)
        .then((res) => {
          const entities = Array.isArray(res?.entities)
            ? res.entities
            : (Array.isArray(res?.entities?.entities) ? res.entities.entities : []);
          if (entities.length > 0) {
            setDxfEntities(entities);
            setTimeout(() => handleFit(entities), 50);
          } else {
            const parsed = parseClientDxf(dxfContent);
            setDxfEntities(parsed);
            setTimeout(() => handleFit(parsed), 50);
          }
        })
        .catch(() => {
          const parsed = parseClientDxf(dxfContent);
          setDxfEntities(parsed);
          setTimeout(() => handleFit(parsed), 50);
        })
        .finally(() => setLoading(false));
    }
  }, [dxfContent]);

  // Convert canvas mouse event to world coordinates in mm
  const getCanvasCoords = (e: React.MouseEvent): { x: number; y: number } => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const worldX = (mouseX - pan.x) / scale;
    const worldY = -(mouseY - pan.y) / scale;

    return { x: worldX, y: worldY };
  };

  // Canvas Render Engine
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Background
    ctx.fillStyle = '#f8fafc';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Grid rendering
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 0.6;
    const gridSize = 20 * scale;
    const offsetX = pan.x % gridSize;
    const offsetY = pan.y % gridSize;
    ctx.beginPath();
    for (let x = offsetX; x < canvas.width; x += gridSize) { ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); }
    for (let y = offsetY; y < canvas.height; y += gridSize) { ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); }
    ctx.stroke();

    // Main Origin Axes (X: Red, Y: Blue)
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.strokeStyle = '#ef4444'; // X axis red
    ctx.moveTo(0, pan.y); ctx.lineTo(canvas.width, pan.y);
    ctx.stroke();

    ctx.beginPath();
    ctx.strokeStyle = '#3b82f6'; // Y axis blue
    ctx.moveTo(pan.x, 0); ctx.lineTo(pan.x, canvas.height);
    ctx.stroke();

    // View Projection Transformation
    ctx.save();
    ctx.translate(pan.x, pan.y);

    if (activeView === 'Top') {
      ctx.scale(1, -1); // Flipped Y projection
    } else if (activeView === 'Right') {
      ctx.scale(0.8, 1); // Side compression
    }

    // Render DXF Entities
    if (dxfEntities && dxfEntities.length > 0) {
      dxfEntities.forEach((entity: any) => {
        if (entity.layer && layers[entity.layer as keyof typeof layers] === false) return;

        ctx.save();
        ctx.setLineDash([]);

        const type = (entity.type || '').toUpperCase();
        const shape = (entity.shape || '').toLowerCase();

        if (entity.layer === 'SHEET_BORDER') {
          ctx.strokeStyle = '#d97706'; // Amber / Gold border
          ctx.lineWidth = 1.8;
          ctx.setLineDash([10, 5]);
          ctx.beginPath();
          const pts = entity.points || entity.vertices || [];
          pts.forEach(([px, py]: [number, number], idx: number) => {
            const x = px * scale; const y = -py * scale;
            if (idx === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          });
          if (entity.closed || entity.is_closed) ctx.closePath();
        } else if (type === 'LINE') {
          ctx.strokeStyle = '#1e293b';
          ctx.lineWidth = 2;
          ctx.beginPath();
          const p1 = entity.points?.[0] || entity.start || [entity.startX ?? 0, entity.startY ?? 0];
          const p2 = entity.points?.[1] || entity.end || [entity.endX ?? 0, entity.endY ?? 0];
          ctx.moveTo((p1[0] ?? 0) * scale, -(p1[1] ?? 0) * scale);
          ctx.lineTo((p2[0] ?? 0) * scale, -(p2[1] ?? 0) * scale);
          ctx.stroke();
        } else if (type === 'CIRCLE' || shape === 'circle' || entity.layer === 'HOLES') {
          ctx.strokeStyle = '#0284c7';
          ctx.lineWidth = 2;
          const cx = (entity.center?.[0] ?? entity.bbox?.cx ?? 0) * scale;
          const cy = -(entity.center?.[1] ?? entity.bbox?.cy ?? 0) * scale;
          const r = (entity.radius !== undefined ? entity.radius : (entity.diameter !== undefined ? entity.diameter / 2 : (entity.bbox?.w ? entity.bbox.w / 2 : 10))) * scale;

          ctx.beginPath();
          ctx.arc(cx, cy, Math.max(1, r), 0, Math.PI * 2);
          ctx.stroke();
        } else if (type === 'ARC') {
          ctx.strokeStyle = '#0284c7';
          ctx.lineWidth = 2;
          const cx = (entity.center?.[0] ?? 0) * scale;
          const cy = -(entity.center?.[1] ?? 0) * scale;
          const r = (entity.radius ?? 10) * scale;
          const startA = ((entity.start_angle ?? 0) * Math.PI) / 180;
          const endA = ((entity.end_angle ?? 360) * Math.PI) / 180;
          ctx.beginPath();
          ctx.arc(cx, cy, Math.max(1, r), startA, endA);
          ctx.stroke();
        } else if (type === 'CENTERLINE' && entity.points) {
          ctx.strokeStyle = '#dc2626';
          ctx.lineWidth = 1;
          ctx.setLineDash([8, 4, 2, 4]);
          ctx.beginPath();
          entity.points.forEach(([px, py]: [number, number], idx: number) => {
            const x = px * scale; const y = -py * scale;
            if (idx === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          });
          ctx.stroke();
        } else if ((type === 'DIMENSION' || type === 'LINEAR_DIMENSION') && entity.p1 && entity.p2 && showDimensions) {
          ctx.strokeStyle = '#4f46e5';
          ctx.fillStyle = '#4f46e5';
          ctx.lineWidth = 1.2;
          ctx.font = 'bold 10px monospace';
          const x1 = entity.p1[0] * scale; const y1 = -entity.p1[1] * scale;
          const x2 = entity.p2[0] * scale; const y2 = -entity.p2[1] * scale;
          ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
          if (entity.text) ctx.fillText(entity.text, (x1 + x2) / 2 - 20, (y1 + y2) / 2 - 5);
        } else if (entity.points && entity.points.length > 0) {
          ctx.strokeStyle = entity.layer === 'OUTLINE' || type === 'LWPOLYLINE' || type === 'POLYLINE' ? '#0f172a' : '#1e293b';
          ctx.lineWidth = entity.layer === 'OUTLINE' ? 2.5 : 2;
          ctx.beginPath();
          entity.points.forEach(([px, py]: [number, number], idx: number) => {
            const x = px * scale; const y = -py * scale;
            if (idx === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          });
          if (entity.closed) ctx.closePath();
          ctx.stroke();
        } else if (entity.vertices && entity.vertices.length > 0) {
          ctx.strokeStyle = '#0f172a';
          ctx.lineWidth = 2;
          ctx.beginPath();
          entity.vertices.forEach(([px, py]: [number, number], idx: number) => {
            const x = px * scale; const y = -py * scale;
            if (idx === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          });
          if (entity.is_closed || entity.closed) ctx.closePath();
          ctx.stroke();
        }

        ctx.restore();
      });

    }

    // Render Live Interactive Drawing Preview
    if (isDrawing && drawStart && drawCurrent) {
      ctx.save();
      ctx.strokeStyle = '#2563eb';
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 4]);

      const sx = drawStart.x * scale; const sy = -drawStart.y * scale;
      const cx = drawCurrent.x * scale; const cy = -drawCurrent.y * scale;

      if (activeTool === 'line') {
        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.lineTo(cx, cy);
        ctx.stroke();
      } else if (activeTool === 'rectangle') {
        ctx.beginPath();
        ctx.rect(sx, sy, cx - sx, cy - sy);
        ctx.stroke();
      } else if (activeTool === 'circle') {
        const radius = Math.sqrt((cx - sx) ** 2 + (cy - sy) ** 2);
        ctx.beginPath();
        ctx.arc(sx, sy, radius, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.restore();
    }

    ctx.restore(); // Restore projection transform

    // Rulers overlay - dynamic tick spacing based on zoom level
    if (showRulers) {
      ctx.fillStyle = '#f1f5f9';
      ctx.fillRect(0, 0, canvas.width, 24);
      ctx.fillRect(0, 0, 24, canvas.height);
      ctx.strokeStyle = '#cbd5e1';
      ctx.fillStyle = '#64748b';
      ctx.font = '9px monospace';
      
      // Dynamic tick spacing based on zoom - keep ticks readable
      const baseSpacing = 50;
      const tickSpacing = Math.max(baseSpacing, baseSpacing / scale);
      const labelSpacing = tickSpacing * 2; // Show labels every 2 ticks
      
      for (let x = 24; x < canvas.width; x += tickSpacing) {
        const worldX = (x - pan.x) / scale;
        const isLabelTick = Math.round((x - 24) / tickSpacing) % 2 === 0;
        
        ctx.beginPath();
        ctx.moveTo(x, isLabelTick ? 14 : 18);
        ctx.lineTo(x, 24);
        ctx.stroke();
        
        if (isLabelTick) {
          ctx.fillText(Math.round(worldX).toString(), x + 2, 12);
        }
      }
      
      for (let y = 24; y < canvas.height; y += tickSpacing) {
        const worldY = -(y - pan.y) / scale;
        const isLabelTick = Math.round((y - 24) / tickSpacing) % 2 === 0;
        
        ctx.beginPath();
        ctx.moveTo(isLabelTick ? 14 : 18, y);
        ctx.lineTo(24, y);
        ctx.stroke();
        
        if (isLabelTick) {
          ctx.save();
          ctx.translate(12, y + 2);
          ctx.rotate(-Math.PI / 2);
          ctx.fillText(Math.round(worldY).toString(), 0, 0);
          ctx.restore();
        }
      }
    }

  }, [dxfEntities, scale, pan, layers, showRulers, showDimensions, activeView, activeTool, isDrawing, drawStart, drawCurrent]);

  // Client-side fallback DXF parser
  const parseClientDxf = (content: string) => {
    const lines = content.split('\n').map((l) => l.trim());
    const entities: any[] = [];
    let currentEntity: any = null;

    for (let i = 0; i < lines.length; i++) {
      const code = lines[i];
      const val = lines[i + 1];

      if (code === '0' && val) {
        if (currentEntity) entities.push(currentEntity);
        currentEntity = { type: val, points: [] };
      } else if (currentEntity) {
        if (code === '8') currentEntity.layer = val;
        if (code === '10') currentEntity.startX = parseFloat(val);
        if (code === '20') currentEntity.startY = parseFloat(val);
        if (code === '11') currentEntity.endX = parseFloat(val);
        if (code === '21') currentEntity.endY = parseFloat(val);
        if (code === '40') currentEntity.radius = parseFloat(val);
      }
    }
    if (currentEntity) entities.push(currentEntity);
    return entities;
  };

  // Mouse Handlers for Pan & Draw
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 1 || e.altKey || activeTool === 'select') {
      // Middle click, Alt, or Select tool: Pan
      setIsPanning(true);
      setStartPan({ x: e.clientX - pan.x, y: e.clientY - pan.y });
    } else if (e.button === 0 && (activeTool as string) !== 'select') {
      // Left click with drawing tool: Start Drawing
      const coords = getCanvasCoords(e);
      setIsDrawing(true);
      setDrawStart(coords);
      setDrawCurrent(coords);
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      setPan({
        x: e.clientX - startPan.x,
        y: e.clientY - startPan.y
      });
    } else if (isDrawing) {
      setDrawCurrent(getCanvasCoords(e));
    }
  };

  const handleMouseUp = () => {
    if (isPanning) {
      setIsPanning(false);
    } else if (isDrawing && drawStart && drawCurrent) {
      setIsDrawing(false);

      // Add drawn entity to dxfEntities and mark dirty
      const newEntity = createEntityFromDrawing(activeTool, drawStart, drawCurrent);
      if (newEntity) {
        const nextEntities = [...(dxfEntities || []), newEntity];
        setDxfEntities(nextEntities);
        markDirty();
      }

      setDrawStart(null);
      setDrawCurrent(null);
    }
  };

  const createEntityFromDrawing = (
    tool: string,
    start: { x: number; y: number },
    end: { x: number; y: number }
  ) => {
    if (tool === 'line') {
      return {
        type: 'LINE',
        layer: 'OUTLINE',
        start: [start.x, start.y],
        end: [end.x, end.y]
      };
    } else if (tool === 'rectangle') {
      const minX = Math.min(start.x, end.x);
      const maxX = Math.max(start.x, end.x);
      const minY = Math.min(start.y, end.y);
      const maxY = Math.max(start.y, end.y);
      return {
        type: 'LWPOLYLINE',
        layer: 'OUTLINE',
        points: [
          [minX, minY],
          [maxX, minY],
          [maxX, maxY],
          [minX, maxY],
          [minX, minY]
        ],
        closed: true
      };
    } else if (tool === 'circle') {
      const radius = Math.sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2);
      return {
        type: 'CIRCLE',
        layer: 'HOLES',
        center: [start.x, start.y],
        radius: Math.max(1, radius)
      };
    }
    return null;
  };

  // Track pan and scale in refs for native event handlers
  const scaleRef = useRef(scale);
  scaleRef.current = scale;
  const panRef = useRef(pan);
  panRef.current = pan;

  // Non-passive Zoom Wheel Listener
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const handleNativeWheel = (e: WheelEvent) => {
      e.preventDefault();
      const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
      const currentScale = scaleRef.current;
      const currentPan = panRef.current;
      const newScale = Math.max(0.05, Math.min(50, currentScale * zoomFactor));

      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      setPan({
        x: mouseX - (mouseX - currentPan.x) * (newScale / currentScale),
        y: mouseY - (mouseY - currentPan.y) * (newScale / currentScale)
      });
      setScale(newScale);
    };

    canvas.addEventListener('wheel', handleNativeWheel, { passive: false });
    return () => {
      canvas.removeEventListener('wheel', handleNativeWheel);
    };
  }, []);

  // Zoom Buttons & Fit
  const handleZoomIn = () => setScale((s) => Math.min(50, s * 1.2));
  const handleZoomOut = () => setScale((s) => Math.max(0.05, s / 1.2));
  const handleFit = (entitiesToFit?: any[]) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ents = entitiesToFit || dxfEntities;
    if (!ents || ents.length === 0) {
      setPan({ x: canvas.width / 2, y: canvas.height / 2 });
      setScale(1.0);
      return;
    }

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    ents.forEach((entity: any) => {
      if (entity.layer === 'SHEET_BORDER') return;
      if (entity.points && Array.isArray(entity.points)) {
        entity.points.forEach(([x, y]: [number, number]) => {
          if (x < minX) minX = x; if (x > maxX) maxX = x;
          if (y < minY) minY = y; if (y > maxY) maxY = y;
        });
      }
      if (entity.center && entity.radius !== undefined) {
        const [cx, cy] = entity.center;
        const r = entity.radius;
        if (cx - r < minX) minX = cx - r; if (cx + r > maxX) maxX = cx + r;
        if (cy - r < minY) minY = cy - r; if (cy + r > maxY) maxY = cy + r;
      }
      if (entity.bbox) {
        const { cx, cy, w, h } = entity.bbox;
        if (cx - w / 2 < minX) minX = cx - w / 2; if (cx + w / 2 > maxX) maxX = cx + w / 2;
        if (cy - h / 2 < minY) minY = cy - h / 2; if (cy + h / 2 > maxY) maxY = cy + h / 2;
      }
    });

    if (minX !== Infinity && maxX !== -Infinity && maxX > minX && maxY > minY) {
      const designW = Math.max(10, maxX - minX);
      const designH = Math.max(10, maxY - minY);
      const centerX = (minX + maxX) / 2;
      const centerY = (minY + maxY) / 2;
      const padding = 60;
      const availableW = Math.max(100, canvas.width - padding * 2);
      const availableH = Math.max(100, canvas.height - padding * 2);
      const fittedScale = Math.min(availableW / designW, availableH / designH, 20.0);
      const finalScale = Math.max(0.1, fittedScale);

      setPan({
        x: canvas.width / 2 - centerX * finalScale,
        y: canvas.height / 2 + centerY * finalScale,
      });
      setScale(finalScale);
    } else {
      setPan({ x: canvas.width / 2, y: canvas.height / 2 });
      setScale(1.0);
    }
  };

  const handleToggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  };

  // Automatic Dimension Annotations
  const handleAutoDim = () => {
    if (!dxfEntities || dxfEntities.length === 0) return;

    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    dxfEntities.forEach((entity: any) => {
      if (entity.layer === 'SHEET_BORDER') return;
      if (entity.points) {
        entity.points.forEach(([x, y]: [number, number]) => {
          if (x < minX) minX = x; if (x > maxX) maxX = x;
          if (y < minY) minY = y; if (y > maxY) maxY = y;
        });
      }
    });

    if (minX !== Infinity && maxX !== -Infinity) {
      const width = Math.round(maxX - minX);
      const height = Math.round(maxY - minY);

      const dimEntities = [
        {
          type: 'DIMENSION',
          layer: 'DIMENSIONS',
          p1: [minX, minY - 15],
          p2: [maxX, minY - 15],
          text: `W: ${width} mm`
        },
        {
          type: 'DIMENSION',
          layer: 'DIMENSIONS',
          p1: [maxX + 15, minY],
          p2: [maxX + 15, maxY],
          text: `H: ${height} mm`
        }
      ];

      setDxfEntities([...dxfEntities, ...dimEntities]);
      markDirty();
    }
  };

  return (
    <div ref={containerRef} className="flex-1 h-full relative bg-slate-900 overflow-hidden font-sans select-none">
      
      {/* 2D Viewport Canvas */}
      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        className="w-full h-full block cursor-crosshair"
      />

      {/* Empty State Prompt */}
      {(!dxfEntities || dxfEntities.length === 0) && (
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-10 text-center px-4">
          <div className="w-12 h-12 rounded-2xl bg-white shadow-md border border-slate-200 flex items-center justify-center mb-3">
            <FileCode className="w-6 h-6 text-indigo-600" />
          </div>
          <h3 className="font-bold text-slate-800 text-sm">2D CAD Canvas Ready</h3>
          <p className="text-xs text-slate-500 max-w-xs mt-1">
            Describe a part in the AI Assistant on the left or use the top vector drawing tools to draw lines, rectangles, and holes.
          </p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center z-20 pointer-events-none">
          <div className="bg-white/90 backdrop-blur rounded-2xl p-4 shadow-lg border border-slate-200 flex items-center space-x-3">
            <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm font-mono text-slate-700">Loading DXF…</span>
          </div>
        </div>
      )}

      {/* Top Toolbar */}
      <div className="absolute top-4 left-4 z-20 flex items-center bg-white/90 backdrop-blur border border-slate-200/90 p-1 rounded-2xl shadow-lg space-x-0.5">
        {(['select', 'line', 'rectangle', 'circle'] as const).map((tool) => {
          const icons = { select: PenTool, line: Slash, rectangle: Square, circle: CircleIcon };
          const Icon = icons[tool];
          return (
            <button key={tool} onClick={() => setActiveTool(tool)}
              className={`p-1.5 rounded-xl transition-colors ${activeTool === tool ? 'bg-indigo-600 text-white font-bold shadow-sm' : 'text-slate-500 hover:bg-slate-100'}`}
              title={tool.charAt(0).toUpperCase() + tool.slice(1) + ' Tool'}>
              <Icon className="w-3.5 h-3.5" />
            </button>
          );
        })}
        <div className="h-4 w-px bg-slate-200 mx-1" />
        <button onClick={() => setShowRulers(!showRulers)}
          className={`p-1.5 rounded-xl text-[10px] flex items-center space-x-1 transition-colors ${showRulers ? 'bg-indigo-50 text-indigo-600 font-bold border border-indigo-200' : 'text-slate-500 hover:bg-slate-100'}`} title="Toggle Coordinate Rulers">
          <Ruler className="w-3.5 h-3.5" /><span>Rulers</span>
        </button>
        <button onClick={handleAutoDim}
          className="p-1.5 rounded-xl text-[10px] text-indigo-600 hover:bg-indigo-50 font-bold flex items-center space-x-1 transition-colors" title="Auto Dimensions">
          <Sparkles className="w-3.5 h-3.5" /><span>Auto-Dim</span>
        </button>
        <button onClick={() => setNestingModalOpen(true)}
          className="p-1.5 rounded-xl text-[10px] text-amber-600 hover:bg-amber-50 font-bold flex items-center space-x-1 transition-colors" title="Nest Parts">
          <Layers3 className="w-3.5 h-3.5" /><span>Nest</span>
        </button>
        <div className="h-4 w-px bg-slate-200 mx-1" />
        <button onClick={undo} disabled={!canUndo()}
          className={`p-1.5 rounded-xl text-[10px] flex items-center space-x-1 transition-colors ${canUndo() ? 'text-slate-600 hover:bg-slate-100 font-bold' : 'text-slate-300 cursor-not-allowed'}`} title="Undo (Ctrl+Z)">
          <Undo className="w-3.5 h-3.5" /><span>Undo</span>
        </button>
        <div className="h-4 w-px bg-slate-200 mx-1" />
        <button onClick={handleZoomIn} className="p-1.5 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors" title="Zoom In"><ZoomIn className="w-3.5 h-3.5" /></button>
        <button onClick={handleZoomOut} className="p-1.5 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors" title="Zoom Out"><ZoomOut className="w-3.5 h-3.5" /></button>
        <button onClick={() => handleFit()} className="p-1.5 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors" title="Fit to View"><Maximize className="w-3.5 h-3.5" /></button>
        <button onClick={handleToggleFullscreen} className="p-1.5 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors" title="Toggle Fullscreen"><Maximize2 className="w-3.5 h-3.5" /></button>
      </div>

      {/* View Projection Selector */}
      <div className="absolute top-4 right-4 z-20 flex items-center bg-white/90 backdrop-blur border border-slate-200/90 p-1 rounded-2xl shadow-lg space-x-0.5 text-[10px]">
        {(['Front', 'Top', 'Right'] as const).map((v) => (
          <button key={v} onClick={() => setActiveView(v)}
            className={`px-2 py-1 rounded-lg transition-all font-medium ${activeView === v ? 'bg-indigo-600 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-100'}`}>
            {v}
          </button>
        ))}
      </div>

      {/* Status & Entity Count Badge */}
      <div className="absolute bottom-4 left-4 z-20 flex items-center space-x-2">
        {dxfEntities && dxfEntities.length > 0 && (
          <div className="bg-white/90 backdrop-blur border border-slate-200 rounded-xl px-3 py-1.5 text-xs font-mono text-slate-600 shadow-sm">
            {dxfEntities.length} vector entities · Scale {scale.toFixed(1)}×
          </div>
        )}
      </div>

    </div>
  );
};
