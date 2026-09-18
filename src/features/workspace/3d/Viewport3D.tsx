import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import * as BufferGeometryUtils from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { use3DWorkspaceStore, Part3D } from '../../../app/store/use3DWorkspaceStore';
import { getStaticFileUrl } from '../../../services/api/client';
import {
  MousePointer, Crosshair, RotateCw, Move, Maximize2,
  Box, Split, ChevronDown, Layers, Loader2, AlertTriangle,
  Component
} from 'lucide-react';
import { cadService } from '../../../services/cad/cadService';

export const Viewport3D: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const meshGroupRef = useRef<THREE.Group | null>(null);
  const sectionHelperRef = useRef<THREE.PlaneHelper | null>(null);

  // Cached geometry by file URL to avoid re-fetching STL on selection or part updates
  const geometryCacheRef = useRef<Map<string, { geometry: THREE.BufferGeometry; origBBox: { lx: number; ly: number; lz: number } }>>(new Map());
  const pendingLoadsRef = useRef<Set<string>>(new Set());

  const {
    activeFilePath, parts, selectedNodeId, selectNode,
    length, width, height, assemblyMode, toggleAssemblyMode
  } = use3DWorkspaceStore();

  const raycasterRef = useRef<THREE.Raycaster>(new THREE.Raycaster());
  const activeToolRef = useRef<string>('orbit');

  const [showWireframe, setShowWireframe] = useState<boolean>(false);
  const toggleWireframe = () => setShowWireframe(v => !v);
  const setInspectionData = (_: any) => { };

  const [loading, setLoading] = useState<boolean>(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeTool, setActiveTool] = useState<string>('orbit');
  const [currentViewLabel, setCurrentViewLabel] = useState<string>('Perspective');
  const [isViewMenuOpen, setIsViewMenuOpen] = useState<boolean>(false);
  const [showSectionPlane, setShowSectionPlane] = useState<boolean>(false);

  // Real clipping plane for cross-section tool (horizontal cutting plane at Y=0)
  const clippingPlaneRef = useRef<THREE.Plane>(new THREE.Plane(new THREE.Vector3(0, -1, 0), 10));

  /** Recursively dispose geometry + material of meshes in a group */
  const disposeGroup = (group: THREE.Group) => {
    while (group.children.length > 0) {
      const child = group.children[0];
      if (child instanceof THREE.Mesh) {
        // Do not dispose cached STL geometries
        let isCached = false;
        for (const entry of geometryCacheRef.current.values()) {
          if (entry.geometry === child.geometry) {
            isCached = true;
            break;
          }
        }
        if (!isCached) {
          child.geometry?.dispose();
        }
        if (Array.isArray(child.material)) {
          child.material.forEach(m => m.dispose());
        } else {
          (child.material as THREE.Material)?.dispose();
        }
      } else if (child instanceof THREE.BoxHelper || child instanceof THREE.PlaneHelper) {
        child.dispose?.();
      }
      group.remove(child);
    }
  };

  // Sync OrbitControls enabled state and constraints with active tool
  useEffect(() => {
    if (!controlsRef.current) return;
    const c = controlsRef.current;
    c.autoRotate = false;

    switch (activeTool) {
      case 'select':
        // Navigation remains interactive while clicks pick parts
        c.enabled = true;
        c.enableRotate = true;
        c.enablePan = true;
        c.enableZoom = true;
        break;
      case 'orbit':
        // Full free navigation: rotate + pan + zoom
        c.enabled = true;
        c.enableRotate = true;
        c.enablePan = true;
        c.enableZoom = true;
        break;
      case 'rotate':
        // Manual rotation focus
        c.enabled = true;
        c.enableRotate = true;
        c.enablePan = false;
        c.enableZoom = true;
        break;
      case 'pan':
      case 'scale':
        // Pan-only drag
        c.enabled = true;
        c.enableRotate = false;
        c.enablePan = true;
        c.enableZoom = true;
        break;
      default:
        c.enabled = true;
        c.enableRotate = true;
        c.enablePan = true;
        c.enableZoom = true;
        break;
    }
    activeToolRef.current = activeTool;
  }, [activeTool]);

  const handleResetView = () => {
    if (!controlsRef.current || !cameraRef.current) return;
    controlsRef.current.reset();
    cameraRef.current.position.set(300, 300, 400);
    controlsRef.current.target.set(0, 0, 0);
    controlsRef.current.update();
    setCurrentViewLabel('Perspective');
  };

  const handleSelectView = (label: string, x: number, y: number, z: number) => {
    if (!controlsRef.current || !cameraRef.current) return;
    cameraRef.current.position.set(x, y, z);
    controlsRef.current.target.set(0, 0, 0);
    controlsRef.current.update();
    setCurrentViewLabel(label);
    setIsViewMenuOpen(false);
  };

  // Toggle real cross-section clipping plane
  const handleToggleSectionPlane = () => {
    setShowSectionPlane(prev => {
      const next = !prev;
      if (!sceneRef.current) return next;

      if (next) {
        if (!sectionHelperRef.current) {
          const helper = new THREE.PlaneHelper(clippingPlaneRef.current, 300, 0x6366f1);
          helper.name = 'sectionPlaneHelper';
          sceneRef.current.add(helper);
          sectionHelperRef.current = helper;
        }
      } else {
        if (sectionHelperRef.current) {
          sceneRef.current.remove(sectionHelperRef.current);
          sectionHelperRef.current.dispose();
          sectionHelperRef.current = null;
        }
      }
      return next;
    });
  };

  // Initialize Three.js scene
  useEffect(() => {
    if (!containerRef.current) return;

    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8fafc);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 5000);
    camera.position.set(300, 300, 400);
    cameraRef.current = camera;

    // High performance renderer with optimized pixel ratio & local clipping enabled
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance'
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    // Disable unused shadow maps for major performance boost during orbit
    renderer.shadowMap.enabled = false;
    renderer.localClippingEnabled = true;
    rendererRef.current = renderer;

    containerRef.current.innerHTML = '';
    containerRef.current.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controlsRef.current = controls;

    // Balanced CAD lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.1);
    dirLight1.position.set(200, 300, 200);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.5);
    dirLight2.position.set(-200, -100, -100);
    scene.add(dirLight2);

    // Group for loaded CAD parts
    const meshGroup = new THREE.Group();
    meshGroupRef.current = meshGroup;
    scene.add(meshGroup);

    // Grid helper
    const gridHelper = new THREE.GridHelper(1000, 100, 0xcbdfeb, 0xe2e8f0);
    gridHelper.name = 'gridHelper';
    scene.add(gridHelper);

    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!containerRef.current || !renderer || !camera) return;
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight;
      if (w === 0 || h === 0) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    let resizeObserver: ResizeObserver | null = null;
    if (typeof ResizeObserver !== 'undefined' && containerRef.current) {
      resizeObserver = new ResizeObserver(() => {
        handleResize();
      });
      resizeObserver.observe(containerRef.current);
    }

    // Canvas click raycaster part picking
    const handleCanvasClick = (e: MouseEvent) => {
      if (!containerRef.current || !cameraRef.current || !meshGroupRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const mouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1
      );
      raycasterRef.current.setFromCamera(mouse, cameraRef.current);
      const meshes: THREE.Mesh[] = [];
      meshGroupRef.current.traverse((child) => {
        if (child instanceof THREE.Mesh && child.userData?.partId) {
          meshes.push(child);
        }
      });

      const intersects = raycasterRef.current.intersectObjects(meshes, false);
      if (intersects.length > 0) {
        const partId = intersects[0].object.userData?.partId;
        if (partId) {
          use3DWorkspaceStore.getState().selectNode(partId);
        }
      }
    };
    containerRef.current.addEventListener('click', handleCanvasClick);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      if (resizeObserver) resizeObserver.disconnect();
      containerRef.current?.removeEventListener('click', handleCanvasClick);
      if (meshGroupRef.current) disposeGroup(meshGroupRef.current);
      controls.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
    };
  }, []);

  // Inspect 3D controller
  const inspectAbortRef = useRef<AbortController | null>(null);
  const inspectedPathRef = useRef<string | null>(null);

  // Helper to load and optimize STL geometry
  const loadSTLGeometry = useCallback(async (filePath: string): Promise<{ geometry: THREE.BufferGeometry; origBBox: { lx: number; ly: number; lz: number } }> => {
    const cached = geometryCacheRef.current.get(filePath);
    if (cached) return cached;

    const url = getStaticFileUrl(filePath);
    const loader = new STLLoader();

    return new Promise((resolve, reject) => {
      loader.load(
        url,
        (rawGeometry) => {
          // Merge duplicated vertices into indexed BufferGeometry to slash vertex count & optimize rendering
          let geometry: THREE.BufferGeometry;
          try {
            geometry = BufferGeometryUtils.mergeVertices(rawGeometry, 1e-4);
          } catch {
            geometry = rawGeometry;
          }

          geometry.computeVertexNormals();
          geometry.center();
          geometry.computeBoundingBox();

          const bb = geometry.boundingBox!;
          const origBBox = {
            lx: Math.max(bb.max.x - bb.min.x, 0.1),
            ly: Math.max(bb.max.y - bb.min.y, 0.1),
            lz: Math.max(bb.max.z - bb.min.z, 0.1),
          };

          const rawCount = rawGeometry.attributes.position?.count || 0;
          const optCount = geometry.attributes.position?.count || 0;
          console.log(`[Viewport3D] STL loaded & optimized | raw vertices: ${rawCount} → indexed vertices: ${optCount} | bbox: ${origBBox.lx.toFixed(1)}x${origBBox.ly.toFixed(1)}x${origBBox.lz.toFixed(1)}mm`);

          const result = { geometry, origBBox };
          geometryCacheRef.current.set(filePath, result);
          resolve(result);
        },
        undefined,
        (err) => reject(err)
      );
    });
  }, []);

  // ── Unified Scene Rendering Effect ──────────────────────────────────────────
  // Re-renders parts whenever parts list, active file, dimensions, selection, wireframe, or assembly mode changes
  useEffect(() => {
    if (!meshGroupRef.current) return;
    const meshGroup = meshGroupRef.current;
    let isCancelled = false;

    const renderScene = async () => {
      // Determine effective parts list
      const effectiveParts = parts.length > 0 ? parts : (activeFilePath ? [{
        id: 'part-main',
        name: '3D Model',
        filePath: activeFilePath,
        visible: true,
        isAssembled: true,
        dimensions: { length, width, height },
        position: { x: 0, y: 0, z: 0 },
        color: '#9ca3af'
      }] : []);

      if (effectiveParts.length === 0) {
        disposeGroup(meshGroup);
        return;
      }

      // Pre-fetch any STL geometries that need loading
      const stlPartsToLoad = effectiveParts.filter(p => p.filePath || (p.id === 'part-main' && activeFilePath));
      for (const p of stlPartsToLoad) {
        const path = p.filePath || activeFilePath;
        if (path && !geometryCacheRef.current.has(path) && !pendingLoadsRef.current.has(path)) {
          pendingLoadsRef.current.add(path);
          setLoading(true);
          setLoadError(null);
          try {
            await loadSTLGeometry(path);
          } catch (err: any) {
            console.error('[Viewport3D] Failed to load STL:', path, err);
            const fname = path.split(/[/\\]/).pop() || 'model.stl';
            setLoadError(`Failed to load 3D model (${fname}).`);
          } finally {
            pendingLoadsRef.current.delete(path);
            setLoading(false);
          }
        }
      }

      if (isCancelled || !meshGroupRef.current) return;
      disposeGroup(meshGroup);

      // Render each part in effectiveParts
      effectiveParts.forEach((part, index) => {
        if (!part.visible) return;

        const isSelected = part.id === selectedNodeId;
        const filePath = part.filePath || (part.id === 'part-main' ? activeFilePath : undefined);
        const cached = filePath ? geometryCacheRef.current.get(filePath) : undefined;

        // Calculate position (with exploded view offset when assemblyMode is false and multiple parts exist)
        const pos = part.position || { x: 0, y: 0, z: 0 };
        const explodeFactor = (!assemblyMode && effectiveParts.length > 1) ? 35 : 0;
        const explodeOffsetX = (index % 2 === 0 ? 1 : -1) * Math.floor((index + 1) / 2) * explodeFactor;
        const explodeOffsetY = Math.floor(index / 2) * explodeFactor;

        let geometry: THREE.BufferGeometry;
        let scaleX = 1;
        let scaleY = 1;
        let scaleZ = 1;

        if (cached) {
          geometry = cached.geometry;
          // Scale to match part dimensions (or workspace L/W/H)
          const targetL = isSelected ? length : (part.dimensions?.length || cached.origBBox.lx);
          const targetH = isSelected ? height : (part.dimensions?.height || cached.origBBox.ly);
          const targetW = isSelected ? width : (part.dimensions?.width || cached.origBBox.lz);

          scaleX = cached.origBBox.lx > 0 ? targetL / cached.origBBox.lx : 1;
          scaleY = cached.origBBox.ly > 0 ? targetH / cached.origBBox.ly : 1;
          scaleZ = cached.origBBox.lz > 0 ? targetW / cached.origBBox.lz : 1;
        } else {
          // CAD Parametric Box geometry
          const dims = part.dimensions || { length: 60, width: 60, height: 40 };
          const pL = isSelected ? length : dims.length;
          const pH = isSelected ? height : dims.height;
          const pW = isSelected ? width : dims.width;

          geometry = new THREE.BoxGeometry(Math.max(pL, 1), Math.max(pH, 1), Math.max(pW, 1));
        }

        const colorHex = part.color
          ? parseInt(part.color.replace('#', ''), 16)
          : 0x9ca3af;

        const material = new THREE.MeshStandardMaterial({
          color: isSelected ? 0x6366f1 : colorHex,
          metalness: isSelected ? 0.25 : 0.15,
          roughness: isSelected ? 0.50 : 0.70,
          wireframe: showWireframe,
          emissive: isSelected ? 0x1e1b4b : 0x000000,
          emissiveIntensity: isSelected ? 0.3 : 0,
          clippingPlanes: showSectionPlane ? [clippingPlaneRef.current] : [],
          clipShadows: true,
          side: THREE.DoubleSide
        });

        const mesh = new THREE.Mesh(geometry, material);
        mesh.userData = { partId: part.id, isStl: !!cached };
        mesh.scale.set(scaleX, scaleY, scaleZ);

        if (cached) {
          mesh.position.set(pos.x + explodeOffsetX, pos.y + explodeOffsetY, pos.z);
        } else {
          const dims = part.dimensions || { length: 60, width: 60, height: 40 };
          const pH = isSelected ? height : dims.height;
          mesh.position.set(pos.x + explodeOffsetX, (pos.z || 0) + pH / 2 + explodeOffsetY, pos.y);
        }

        meshGroup.add(mesh);

        // Add selection helper
        if (isSelected) {
          const highlightBox = new THREE.BoxHelper(mesh, 0x38bdf8);
          meshGroup.add(highlightBox);
        }
      });

      // Trigger inspect-3D once for new active file
      if (activeFilePath && inspectedPathRef.current !== activeFilePath) {
        console.log(`[Viewport3D] New active file detected: ${activeFilePath}`);
        inspectedPathRef.current = activeFilePath;
        inspectAbortRef.current?.abort();
        inspectAbortRef.current = new AbortController();
        
        console.log(`[Viewport3D] Starting inspect-3D for: ${activeFilePath}`);
        cadService.clearInspectionCache(activeFilePath);
        cadService.inspect3D(activeFilePath, inspectAbortRef.current.signal)
          .then((result) => {
            console.log(`[Viewport3D] inspect-3D completed successfully for: ${activeFilePath}`);
            setInspectionData(result);
          })
          .catch((err: any) => {
            console.log(`[Viewport3D] inspect-3D failed for ${activeFilePath}:`, err);
            if (err?.name !== 'CanceledError' && err?.name !== 'AbortError') {
              inspectedPathRef.current = null;
            }
          });
      }
    };

    renderScene();

    return () => {
      isCancelled = true;
    };
  }, [parts, activeFilePath, selectedNodeId, length, width, height, showWireframe, showSectionPlane, assemblyMode, loadSTLGeometry]);

  return (
    <div className="relative flex-1 bg-[#F8FAFC] overflow-hidden select-none font-sans">
      {/* 3D WebGL Canvas Container */}
      <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Top Left Axis Orientation Triad Gizmo Overlay */}
      <div className="absolute top-4 left-4 z-20 pointer-events-none">
        <svg viewBox="0 0 100 100" className="w-16 h-16">
          {/* Z Axis (Green) */}
          <line x1="30" y1="70" x2="30" y2="25" stroke="#10B981" strokeWidth="2.5" strokeLinecap="round" />
          <text x="26" y="20" fill="#10B981" fontSize="11" fontWeight="bold">Z</text>
          {/* X Axis (Red) */}
          <line x1="30" y1="70" x2="75" y2="70" stroke="#EF4444" strokeWidth="2.5" strokeLinecap="round" />
          <text x="80" y="74" fill="#EF4444" fontSize="11" fontWeight="bold">X</text>
          {/* Y Axis (Blue) */}
          <line x1="30" y1="70" x2="10" y2="85" stroke="#3B82F6" strokeWidth="2.5" strokeLinecap="round" />
          <text x="2" y="94" fill="#3B82F6" fontSize="11" fontWeight="bold">Y</text>
        </svg>
      </div>

      {/* Top Right View Options */}
      <div className="absolute top-4 right-4 z-20 flex items-center space-x-2">
        <div className="relative">
          <button
            onClick={() => setIsViewMenuOpen(!isViewMenuOpen)}
            className="flex items-center space-x-1.5 bg-white border border-slate-200 px-3 py-1.5 rounded-xl shadow-xs text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <span>{currentViewLabel}</span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {isViewMenuOpen && (
            <div className="absolute right-0 top-full mt-1 w-36 bg-white border border-slate-200 rounded-xl shadow-lg py-1 z-30 font-medium text-xs text-slate-700">
              <button
                onClick={() => handleSelectView('Perspective', 150, 150, 200)}
                className="w-full text-left px-3 py-1.5 hover:bg-slate-50 hover:text-indigo-600 transition-colors block"
              >
                Perspective (3D)
              </button>
              <button
                onClick={() => handleSelectView('Top View', 0, 300, 0.001)}
                className="w-full text-left px-3 py-1.5 hover:bg-slate-50 hover:text-indigo-600 transition-colors block"
              >
                Top (XY)
              </button>
              <button
                onClick={() => handleSelectView('Front View', 0, 0, 300)}
                className="w-full text-left px-3 py-1.5 hover:bg-slate-50 hover:text-indigo-600 transition-colors block"
              >
                Front (XZ)
              </button>
              <button
                onClick={() => handleSelectView('Side View', 300, 0, 0)}
                className="w-full text-left px-3 py-1.5 hover:bg-slate-50 hover:text-indigo-600 transition-colors block"
              >
                Right Side (YZ)
              </button>
            </div>
          )}
        </div>

        <button
          onClick={handleResetView}
          className="bg-white border border-slate-200 px-3 py-1.5 rounded-xl shadow-xs text-xs font-semibold text-slate-700 hover:bg-slate-50 hover:text-indigo-600 transition-colors"
        >
          Reset View
        </button>
      </div>

      {/* Center Viewport Message overlay */}
      {!activeFilePath && parts.length === 0 && (
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-indigo-50 flex items-center justify-center text-indigo-400">
            <Box className="w-6 h-6 stroke-1" />
          </div>
          <h3 className="text-sm font-bold text-slate-700">3D Viewport</h3>
          <p className="text-xs text-slate-400">Add parts in the Model Tree or generate a 3D model</p>
        </div>
      )}

      {/* Floating Bottom CAD Toolbar */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex items-center bg-white/90 backdrop-blur border border-slate-200/90 px-3 py-1.5 rounded-2xl shadow-lg space-x-2">
        <button
          onClick={() => setActiveTool('select')}
          className={`p-2 rounded-xl transition-colors ${activeTool === 'select' ? 'bg-indigo-50 text-indigo-600' : 'text-slate-500 hover:bg-slate-100'}`}
          title="Select Part (Click parts to select)"
        >
          <MousePointer className="w-4 h-4" />
        </button>

        <button
          onClick={() => setActiveTool('orbit')}
          className={`p-2 rounded-xl transition-colors ${activeTool === 'orbit' ? 'bg-indigo-50 text-indigo-600' : 'text-slate-500 hover:bg-slate-100'}`}
          title="Free Orbit (Rotate, Pan & Zoom)"
        >
          <Crosshair className="w-4 h-4" />
        </button>

        <button
          onClick={() => setActiveTool('rotate')}
          className={`p-2 rounded-xl transition-colors ${activeTool === 'rotate' ? 'bg-indigo-50 text-indigo-600' : 'text-slate-500 hover:bg-slate-100'}`}
          title="Manual 3D Rotate"
        >
          <RotateCw className="w-4 h-4" />
        </button>

        <button
          onClick={() => setActiveTool('pan')}
          className={`p-2 rounded-xl transition-colors ${activeTool === 'pan' ? 'bg-indigo-50 text-indigo-600' : 'text-slate-500 hover:bg-slate-100'}`}
          title="Pan / Move (drag to translate view)"
        >
          <Move className="w-4 h-4" />
        </button>

        <div className="h-4 w-px bg-slate-200" />

        <button
          onClick={toggleWireframe}
          className={`p-2 rounded-xl transition-colors ${showWireframe ? 'bg-indigo-50 text-indigo-600' : 'text-slate-500 hover:bg-slate-100'}`}
          title="Toggle Solid / Wireframe"
        >
          <Layers className="w-4 h-4" />
        </button>

        <button
          onClick={handleToggleSectionPlane}
          className={`p-2 rounded-xl transition-colors ${showSectionPlane ? 'bg-indigo-50 text-indigo-600' : 'text-slate-500 hover:bg-slate-100'}`}
          title="Toggle Cross-Section Slicing Plane"
        >
          <Split className="w-4 h-4" />
        </button>

        <button
          onClick={toggleAssemblyMode}
          className={`p-2 rounded-xl transition-colors ${assemblyMode ? 'bg-indigo-50 text-indigo-600' : 'text-slate-500 hover:bg-slate-100'}`}
          title={assemblyMode ? "Assembly View (Active) - Click for Exploded View" : "Exploded View (Active) - Click for Assembled View"}
        >
          <Component className="w-4 h-4" />
        </button>

        <button
          onClick={() => containerRef.current?.requestFullscreen()}
          className="p-2 rounded-xl text-slate-500 hover:bg-slate-100 transition-colors"
          title="Fullscreen Viewport"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>

      {/* 3D Loading Spinner Overlay */}
      {loading && (
        <div className="absolute inset-0 bg-slate-900/10 backdrop-blur-[1px] flex items-center justify-center z-30 pointer-events-none">
          <div className="bg-white/95 border border-slate-200 px-4 py-3 rounded-2xl shadow-lg flex items-center space-x-3">
            <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
            <span className="text-xs font-semibold text-slate-700">Loading 3D CAD model…</span>
          </div>
        </div>
      )}

      {/* 3D Load Error Alert */}
      {loadError && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-30 max-w-md bg-rose-50 border border-rose-200 text-rose-800 px-4 py-3 rounded-2xl shadow-md flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
          <div className="flex-1 text-xs">
            <p className="font-semibold">3D Model Load Error</p>
            <p className="text-rose-600 mt-0.5">{loadError}</p>
          </div>
          <button
            onClick={() => {
              setLoadError(null);
              const cur = activeFilePath;
              use3DWorkspaceStore.getState().setActiveFile(null);
              setTimeout(() => use3DWorkspaceStore.getState().setActiveFile(cur), 50);
            }}
            className="text-[11px] font-bold bg-rose-100 hover:bg-rose-200 text-rose-700 px-2.5 py-1 rounded-lg transition-colors shrink-0"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
};
