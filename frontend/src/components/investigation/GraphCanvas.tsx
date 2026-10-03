import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  Minimize2,
  Filter, 
  Layers, 
  AlertOctagon, 
  X, 
  Smartphone, 
  CreditCard, 
  User, 
  Globe, 
  FolderArchive, 
  Move,
  ChevronDown,
  Check,
  RotateCcw
} from 'lucide-react';
import type { GraphNode, GraphEdge } from '../../types/investigation';

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  caseId: string;
  isInvestigating?: boolean;
  isTerminalOpen?: boolean;
}

export const GraphCanvas: React.FC<GraphCanvasProps> = ({
  nodes: initialNodes,
  edges,
  caseId,
  isTerminalOpen = false,
}) => {
  const [nodes, setNodes] = useState<GraphNode[]>(initialNodes);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [activeFilter, setActiveFilter] = useState<string>('all');
  const [isFilterDropdownOpen, setIsFilterDropdownOpen] = useState<boolean>(false);
  const [showEdgeLabels, setShowEdgeLabels] = useState<boolean>(true);
  const [zoomLevel, setZoomLevel] = useState<number>(1.0);
  const [userPanOffset, setUserPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDraggingCanvas, setIsDraggingCanvas] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [nodeDragOffset, setNodeDragOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isMaximized, setIsMaximized] = useState<boolean>(false);
  const [containerSize, setContainerSize] = useState<{ width: number; height: number }>({
    width: 900,
    height: 520,
  });

  const containerRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // ResizeObserver and resize listener to keep container viewport dimensions accurate
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
          setContainerSize({
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          });
        }
      }
    };

    updateSize();
    window.addEventListener('resize', updateSize);
    let ro: ResizeObserver | null = null;
    if (typeof ResizeObserver !== 'undefined' && containerRef.current) {
      ro = new ResizeObserver(() => updateSize());
      ro.observe(containerRef.current);
    }

    return () => {
      window.removeEventListener('resize', updateSize);
      if (ro) ro.disconnect();
    };
  }, [isMaximized]);

  // Stable reference bounding box derived from initial case topology
  // Independent of individual node dragging so canvas camera coordinates remain rigid
  const baseBounds = useMemo(() => {
    if (initialNodes.length === 0) {
      return { minX: 100, maxX: 800, minY: 50, maxY: 350, width: 700, height: 300, centerX: 450, centerY: 200 };
    }
    const xs = initialNodes.map(n => (typeof n.x === 'number' ? n.x : 440));
    const ys = initialNodes.map(n => (typeof n.y === 'number' ? n.y : 220));

    // Each node card is 130px wide (-65 to +65) and 56px high (-28 to +28)
    let minX = Math.min(...xs) - 75;
    let maxX = Math.max(...xs) + 75;
    let minY = Math.min(...ys) - 35;
    let maxY = Math.max(...ys) + 35;

    // Expand bounds if coordinated ring cluster aura is present
    if (initialNodes.some(n => n.isFraudRing)) {
      minY = Math.min(minY, 20); // cluster text at y = 32
      maxX = Math.max(maxX, 640 + 260); // aura ellipse at cx=640, rx=250
    }

    const width = Math.max(maxX - minX, 100);
    const height = Math.max(maxY - minY, 100);

    return {
      minX,
      maxX,
      minY,
      maxY,
      width,
      height,
      centerX: (minX + maxX) / 2,
      centerY: (minY + maxY) / 2,
    };
  }, [initialNodes]);

  // Compute optimal zoom to fit the entire graph into the visible container
  const computeFitZoom = useCallback((w: number, h: number) => {
    if (w <= 0 || h <= 0 || baseBounds.width <= 0 || baseBounds.height <= 0) return 1.0;
    // Margins: 70px horizontal, 100px vertical (toolbar and legend padding)
    const availW = Math.max(w - 70, 200);
    const availH = Math.max(h - 100, 200);

    const scaleX = availW / baseBounds.width;
    const scaleY = availH / baseBounds.height;
    const fit = Math.min(scaleX, scaleY);
    // Clamp to a clear, legible range (0.65 to 1.35)
    return Math.min(Math.max(Number(fit.toFixed(2)), 0.65), 1.35);
  }, [baseBounds]);

  // Effective SVG pan:
  // - Horizontally centered in the container
  // - Initially (terminal closed): vertically centered in the middle of the available canvas
  // - When terminal opens: moves smoothly up to the top anchor (y = 56px) so all nodes fit above terminal
  // - Uses baseBounds so dragging any individual node NEVER moves the overall canvas
  const effectivePan = useMemo(() => {
    let targetY: number;

    if (isTerminalOpen) {
      // Anchored to top under toolbar
      const topAnchorY = 56;
      targetY = topAnchorY - baseBounds.minY * zoomLevel;
    } else {
      // Balanced in the middle of the available canvas
      targetY = containerSize.height / 2 - baseBounds.centerY * zoomLevel;
    }

    return {
      x: Math.round(containerSize.width / 2 - baseBounds.centerX * zoomLevel + userPanOffset.x),
      y: Math.round(targetY + userPanOffset.y),
    };
  }, [containerSize.width, containerSize.height, baseBounds.centerX, baseBounds.centerY, baseBounds.minY, zoomLevel, userPanOffset.x, userPanOffset.y, isTerminalOpen]);

  // Keyboard shortcut: Escape to exit maximized mode
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isMaximized) {
        setIsMaximized(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMaximized]);

  // Smooth Zoom In: expands symmetrically around graph center
  const handleZoomIn = useCallback(() => {
    if (isMaximized) return; // Zoom feature should not work while enlarged
    setZoomLevel(prev => Math.min(Number((prev + 0.15).toFixed(2)), 2.5));
  }, [isMaximized]);

  // Smooth Zoom Out: contracts symmetrically towards graph center
  const handleZoomOut = useCallback(() => {
    if (isMaximized) return; // Zoom feature should not work while enlarged
    setZoomLevel(prev => Math.max(Number((prev - 0.15).toFixed(2)), 0.5));
  }, [isMaximized]);

  // Reset Pan and Zoom to auto-fitted default
  const handleResetZoomPan = useCallback(() => {
    if (isMaximized) return;
    const fit = computeFitZoom(containerSize.width, containerSize.height);
    setZoomLevel(fit);
    setUserPanOffset({ x: 0, y: 0 });
  }, [isMaximized, computeFitZoom, containerSize.width, containerSize.height]);

  // Mouse wheel zoom towards center (disabled when maximized)
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const onWheel = (e: WheelEvent) => {
      if (isMaximized) return;
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 0.08 : -0.08;
      setZoomLevel(prev => Math.min(Math.max(Number((prev + zoomFactor).toFixed(2)), 0.5), 2.5));
    };

    container.addEventListener('wheel', onWheel, { passive: false });
    return () => container.removeEventListener('wheel', onWheel);
  }, [isMaximized]);

  // Sync and auto-fit when case changes
  useEffect(() => {
    setNodes(initialNodes);
    setSelectedNode(null);
    setUserPanOffset({ x: 0, y: 0 });
    const fit = computeFitZoom(containerSize.width, containerSize.height);
    setZoomLevel(fit);
    setActiveFilter('all');
    setIsFilterDropdownOpen(false);
  }, [caseId, initialNodes, computeFitZoom, containerSize.width, containerSize.height]);

  // Click outside to close filter dropdown
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsFilterDropdownOpen(false);
      }
    };
    if (isFilterDropdownOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [isFilterDropdownOpen]);

  // Filter options with counts and colors
  const filterOptions = useMemo(() => [
    { key: 'all', label: 'All Entities', count: nodes.length, color: 'bg-slate-900' },
    { key: 'transaction', label: 'Transaction', count: nodes.filter(n => n.type.toLowerCase() === 'transaction').length, color: 'bg-rose-600' },
    { key: 'device', label: 'Device', count: nodes.filter(n => n.type.toLowerCase() === 'device').length, color: 'bg-emerald-600' },
    { key: 'account', label: 'Account', count: nodes.filter(n => n.type.toLowerCase() === 'account').length, color: 'bg-sky-600' },
    { key: 'card', label: 'Card', count: nodes.filter(n => n.type.toLowerCase() === 'card').length, color: 'bg-purple-600' },
    { key: 'ip', label: 'IP Address', count: nodes.filter(n => n.type.toLowerCase() === 'ip').length, color: 'bg-amber-600' },
    { key: 'priorcase', label: 'Prior Case', count: nodes.filter(n => n.type.toLowerCase() === 'priorcase').length, color: 'bg-rose-500' },
  ], [nodes]);

  const activeOption = filterOptions.find(o => o.key === activeFilter) || filterOptions[0];

  // Filter nodes based on entity type
  const filteredNodes = useMemo(() => {
    if (activeFilter === 'all') return nodes;
    return nodes.filter(n => n.type.toLowerCase() === activeFilter.toLowerCase());
  }, [nodes, activeFilter]);

  const visibleNodeIds = useMemo(() => new Set(filteredNodes.map(n => n.id)), [filteredNodes]);

  // Filter edges based on visible nodes
  const visibleEdges = useMemo(() => {
    return edges.filter(e => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target));
  }, [edges, visibleNodeIds]);

  // Identify nodes in fraud ring
  const fraudRingNodes = useMemo(() => {
    return nodes.filter(n => n.isFraudRing);
  }, [nodes]);

  // Node Drag handling: store offset between mouse cursor and node center
  const handleNodeMouseDown = (e: React.MouseEvent, nodeId: string) => {
    e.stopPropagation();
    const node = nodes.find(n => n.id === nodeId);
    if (!node || !containerRef.current) return;

    setSelectedNode(node);
    setDraggingNodeId(nodeId);

    const rect = containerRef.current.getBoundingClientRect();
    const mouseWorldX = (e.clientX - rect.left - effectivePan.x) / zoomLevel;
    const mouseWorldY = (e.clientY - rect.top - effectivePan.y) / zoomLevel;

    setNodeDragOffset({
      x: mouseWorldX - (node.x ?? 400),
      y: mouseWorldY - (node.y ?? 200),
    });
  };

  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsDraggingCanvas(true);
      setDragStart({ x: e.clientX - userPanOffset.x, y: e.clientY - userPanOffset.y });
    }
  };

  // Global mouse handlers keep dragging smooth even if cursor moves fast
  useEffect(() => {
    if (!draggingNodeId && !isDraggingCanvas) return;

    const onGlobalMouseMove = (e: MouseEvent) => {
      if (draggingNodeId && containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        const mouseWorldX = (e.clientX - rect.left - effectivePan.x) / zoomLevel;
        const mouseWorldY = (e.clientY - rect.top - effectivePan.y) / zoomLevel;

        const newX = Math.round(mouseWorldX - nodeDragOffset.x);
        const newY = Math.round(mouseWorldY - nodeDragOffset.y);

        setNodes(prev => prev.map(n => {
          if (n.id === draggingNodeId) {
            return { ...n, x: newX, y: newY };
          }
          return n;
        }));
      } else if (isDraggingCanvas) {
        setUserPanOffset({
          x: e.clientX - dragStart.x,
          y: e.clientY - dragStart.y,
        });
      }
    };

    const onGlobalMouseUp = () => {
      setDraggingNodeId(null);
      setIsDraggingCanvas(false);
    };

    window.addEventListener('mousemove', onGlobalMouseMove);
    window.addEventListener('mouseup', onGlobalMouseUp);

    return () => {
      window.removeEventListener('mousemove', onGlobalMouseMove);
      window.removeEventListener('mouseup', onGlobalMouseUp);
    };
  }, [draggingNodeId, isDraggingCanvas, effectivePan.x, effectivePan.y, zoomLevel, nodeDragOffset, dragStart]);

  // Node styling helper matching Image 3
  const getNodeVisuals = (node: GraphNode) => {
    const isSelected = selectedNode?.id === node.id;
    const fill = '#FFFFFF';
    let stroke = '#64748B';
    let icon = <Layers className="w-3.5 h-3.5" />;

    switch (node.type) {
      case 'Transaction':
        stroke = '#E11D48';
        icon = <AlertOctagon className="w-4 h-4 text-rose-600" />;
        break;
      case 'Account':
        stroke = '#0284C7';
        icon = <User className="w-3.5 h-3.5 text-sky-600" />;
        break;
      case 'Card':
        stroke = '#7C3AED';
        icon = <CreditCard className="w-3.5 h-3.5 text-purple-600" />;
        break;
      case 'Device':
        stroke = '#16A34A';
        icon = <Smartphone className="w-3.5 h-3.5 text-emerald-600" />;
        break;
      case 'IP':
        stroke = '#D97706';
        icon = <Globe className="w-3.5 h-3.5 text-amber-600" />;
        break;
      case 'PriorCase':
        stroke = '#E11D48';
        icon = <FolderArchive className="w-3.5 h-3.5 text-rose-600" />;
        break;
    }

    return { fill, stroke, icon, isSelected };
  };

  return (
    <div className={`transition-all duration-200 flex flex-col select-none ${
      isMaximized 
        ? 'fixed inset-0 z-50 bg-white w-screen h-screen' 
        : 'relative flex-1 min-h-0 w-full bg-slate-50/70 overflow-hidden'
    }`}>
      {/* Top Floating Graph Toolbar with Dropdown Menu */}
      <div className="absolute top-3 left-3 right-3 z-20 flex items-center justify-between pointer-events-none">
        {/* Dropdown Menu for Filters */}
        <div ref={dropdownRef} className="pointer-events-auto relative flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setIsFilterDropdownOpen(prev => !prev)}
            className="flex items-center space-x-2 bg-white/95 backdrop-blur-md border border-slate-200 hover:border-slate-300 shadow-sm px-3 py-1.5 rounded-lg text-xs transition-colors focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            <span className="font-semibold text-slate-600 text-[11px]">Filter:</span>
            <span className="px-2 py-0.5 rounded bg-slate-900 text-white font-bold text-[10.5px] font-mono">
              {activeOption.label}
            </span>
            <span className="text-[10px] text-slate-400 font-mono">({activeOption.count})</span>
            <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-150 ${isFilterDropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {/* Reset filter button if not all */}
          {activeFilter !== 'all' && (
            <button
              type="button"
              onClick={() => setActiveFilter('all')}
              className="flex items-center gap-1 px-2 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 text-[10.5px] font-medium shadow-xs"
              title="Reset to All Entities"
            >
              <RotateCcw className="w-3 h-3 text-slate-400" />
              <span>Reset</span>
            </button>
          )}

          {/* Dropdown Menu Popup */}
          {isFilterDropdownOpen && (
            <div className="absolute top-full left-0 mt-1.5 w-52 bg-white border border-slate-200 rounded-xl shadow-lg p-1.5 z-30 animate-in fade-in slide-in-from-top-1 duration-100">
              <div className="px-2 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider font-mono">
                Entity Types
              </div>
              <div className="space-y-0.5">
                {filterOptions.map((opt) => {
                  const isCurrent = activeFilter === opt.key;
                  return (
                    <button
                      key={opt.key}
                      type="button"
                      onClick={() => {
                        setActiveFilter(opt.key);
                        setIsFilterDropdownOpen(false);
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                        isCurrent 
                          ? 'bg-indigo-50 text-indigo-700 font-semibold' 
                          : 'text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center space-x-2">
                        <span className={`w-2 h-2 rounded-full ${opt.color}`} />
                        <span>{opt.label}</span>
                      </div>
                      <div className="flex items-center space-x-1.5">
                        <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded ${
                          isCurrent ? 'bg-indigo-100 text-indigo-800 font-bold' : 'bg-slate-100 text-slate-500'
                        }`}>
                          {opt.count}
                        </span>
                        {isCurrent && <Check className="w-3.5 h-3.5 text-indigo-600 stroke-[2.5]" />}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Canvas Controls: Zoom (hidden when enlarged), Maximize/Minimize, Labels */}
        <div className="pointer-events-auto flex items-center space-x-1 bg-white/95 backdrop-blur-md border border-slate-200 shadow-sm p-1 rounded-lg text-xs">
          {!isMaximized && (
            <>
              <button
                type="button"
                onClick={handleZoomIn}
                className="p-1 rounded hover:bg-slate-100 text-slate-700 transition-colors"
                title="Zoom In"
              >
                <ZoomIn className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={handleZoomOut}
                className="p-1 rounded hover:bg-slate-100 text-slate-700 transition-colors"
                title="Zoom Out"
              >
                <ZoomOut className="w-4 h-4" />
              </button>
              
              <button
                type="button"
                onClick={handleResetZoomPan}
                className="px-1.5 py-0.5 rounded text-[11px] font-mono text-slate-600 hover:bg-slate-100 hover:text-indigo-600 font-semibold transition-colors"
                title="Reset Pan & Zoom"
              >
                {Math.round(zoomLevel * 100)}%
              </button>

              <div className="h-3 w-px bg-slate-200 mx-0.5" />
            </>
          )}

          <button
            type="button"
            onClick={() => setIsMaximized(prev => !prev)}
            className={`p-1 rounded transition-colors ${
              isMaximized ? 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200' : 'hover:bg-slate-100 text-slate-700'
            }`}
            title={isMaximized ? "Exit Fullscreen (Esc)" : "Enlarge Graph to Fullscreen"}
          >
            {isMaximized ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </button>

          <div className="h-3 w-px bg-slate-200 mx-0.5" />

          <button
            type="button"
            onClick={() => setShowEdgeLabels(!showEdgeLabels)}
            className={`px-2 py-0.5 rounded text-[10.5px] font-medium transition-colors ${
              showEdgeLabels ? 'bg-indigo-50 text-indigo-700 border border-indigo-200 font-semibold' : 'text-slate-500 hover:bg-slate-100 border border-transparent'
            }`}
            title="Toggle Edge Labels"
          >
            <span>Labels</span>
          </button>
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div 
        ref={containerRef}
        onMouseDown={handleCanvasMouseDown}
        className={`flex-1 min-h-0 w-full relative overflow-hidden cursor-${isDraggingCanvas ? 'grabbing' : 'grab'}`}
      >
        {/* Empty Canvas Placeholder when no case is selected */}
        {nodes.length === 0 && (
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none select-none z-10 p-6">
            <div className="relative flex items-center justify-center mb-4">
              <div className="w-16 h-16 rounded-full border border-dashed border-slate-300 flex items-center justify-center animate-[spin_20s_linear_infinite]" />
              <div className="absolute w-10 h-10 rounded-full bg-white border border-slate-200/90 shadow-2xs flex items-center justify-center text-slate-400">
                <Layers className="w-5 h-5 text-indigo-500/80" />
              </div>
            </div>
            <div className="text-xs font-bold text-slate-700 font-mono tracking-widest uppercase">
              Topology Engine Ready
            </div>
            <div className="text-[11.5px] text-slate-400 mt-1.5 max-w-sm text-center font-normal leading-relaxed">
              Select an investigation case from the dropdown to map real-time transaction topologies, device links, and entity clusters.
            </div>
          </div>
        )}

        <svg 
          className="w-full h-full"
          style={{
            backgroundImage: 'radial-gradient(#CBD5E1 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }}
        >
          <g 
            transform={`translate(${effectivePan.x}, ${effectivePan.y}) scale(${zoomLevel})`}
            className={isDraggingCanvas || draggingNodeId ? '' : 'transition-transform duration-300 ease-out'}
          >
            {/* Coordinated Ring Cluster Bounding Aura matching Image 3 */}
            {fraudRingNodes.length > 0 && (
              <g className="pointer-events-none">
                <ellipse
                  cx={640}
                  cy={185}
                  rx={250}
                  ry={155}
                  fill="rgba(244, 63, 94, 0.04)"
                  stroke="#fb7185"
                  strokeWidth="1.5"
                  strokeDasharray="4 3"
                />
                <text
                  x={640}
                  y={32}
                  textAnchor="middle"
                  className="fill-rose-600 font-extrabold text-[10.5px] tracking-widest uppercase font-mono"
                >
                  COORDINATED RING CLUSTER
                </text>
              </g>
            )}

            {/* Edge Lines */}
            {visibleEdges.map((edge) => {
              const sourceNode = nodes.find(n => n.id === edge.source);
              const targetNode = nodes.find(n => n.id === edge.target);
              if (!sourceNode || !targetNode) return null;

              const x1 = sourceNode.x || 400;
              const y1 = sourceNode.y || 200;
              const x2 = targetNode.x || 400;
              const y2 = targetNode.y || 200;
              const midX = (x1 + x2) / 2;
              const midY = (y1 + y2) / 2;
              const labelWidth = Math.max(68, edge.label.length * 6.5 + 16);

              return (
                <g key={edge.id} className="transition-opacity duration-300">
                  <line
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke={edge.isSuspicious ? '#E11D48' : '#94A3B8'}
                    strokeWidth={edge.isSuspicious ? '1.8' : '1.2'}
                    strokeDasharray={edge.isSuspicious ? '4 3' : 'none'}
                    className={edge.isSuspicious ? 'animate-dash' : ''}
                  />
                  {showEdgeLabels && (
                    <g transform={`translate(${midX}, ${midY})`}>
                      <rect
                        x={-labelWidth / 2}
                        y="-9"
                        width={labelWidth}
                        height="18"
                        rx="4"
                        fill="#FFFFFF"
                        stroke={edge.isSuspicious ? '#FECDD3' : '#E2E8F0'}
                        strokeWidth="1"
                        className="shadow-xs"
                      />
                      <text
                        textAnchor="middle"
                        y="3.5"
                        className={`text-[8.5px] font-mono font-bold ${
                          edge.isSuspicious ? 'fill-rose-600' : 'fill-slate-600'
                        }`}
                      >
                        {edge.label}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}

            {/* Nodes matching Image 3 geometry */}
            {filteredNodes.map((node) => {
              const { fill, stroke, isSelected } = getNodeVisuals(node);
              const nx = node.x || 400;
              const ny = node.y || 200;
              const lines = node.label.split('\n');

              return (
                <g
                  key={node.id}
                  transform={`translate(${nx}, ${ny})`}
                  onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedNode(node);
                  }}
                  className="cursor-pointer group"
                >
                  {/* Selection Glow */}
                  {isSelected && (
                    <rect
                      x="-74"
                      y="-37"
                      width="148"
                      height="74"
                      rx="12"
                      fill="none"
                      stroke="#4F46E5"
                      strokeWidth="2.5"
                      className="animate-pulse"
                    />
                  )}

                  {/* Red Dashed Outline for Fraud Entities matching Image 3 */}
                  {node.isFraudRing && (
                    <rect
                      x="-71"
                      y="-34"
                      width="142"
                      height="68"
                      rx="10"
                      fill="none"
                      stroke="#E11D48"
                      strokeWidth="1.8"
                      strokeDasharray="4 3"
                    />
                  )}

                  {/* Node Capsule Card */}
                  <rect
                    x="-65"
                    y="-28"
                    width="130"
                    height="56"
                    rx="8"
                    fill={fill}
                    stroke={stroke}
                    strokeWidth={isSelected ? '2' : '1.8'}
                    className="shadow-xs transition-transform duration-100 group-hover:scale-[1.02]"
                  />

                  {/* Node Header Badge with Entity Type */}
                  <rect
                    x="-58"
                    y="-24"
                    width="116"
                    height="15"
                    rx="3"
                    fill="#FFFFFF"
                    stroke="#E2E8F0"
                    strokeWidth="0.8"
                  />
                  <text
                    x="0"
                    y="-13"
                    textAnchor="middle"
                    className="font-mono text-[8.5px] font-bold fill-slate-700 tracking-wider uppercase"
                  >
                    {node.type}
                  </text>

                  {/* Node Text Content: Line 1 Name */}
                  <text
                    x="0"
                    y="4"
                    textAnchor="middle"
                    className="font-mono text-[9.5px] font-bold fill-slate-900"
                  >
                    {lines[0]}
                  </text>

                  {/* Line 2 Subtitle / Value */}
                  {lines[1] && (
                    <text
                      x="0"
                      y="17"
                      textAnchor="middle"
                      className="font-mono text-[8.5px] font-semibold fill-slate-500"
                    >
                      {lines[1]}
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        </svg>

        {/* Node Detail Slide-in Card (Inspector) */}
        {selectedNode && (
          <div className="absolute right-3 bottom-3 w-72 bg-white/95 backdrop-blur-md border border-slate-200 rounded-xl shadow-popup p-3.5 z-20 animate-in fade-in slide-in-from-bottom-2 duration-150">
            <div className="flex items-start justify-between border-b border-slate-100 pb-2 mb-2.5">
              <div className="flex items-center space-x-2">
                <div className="p-1 rounded bg-slate-100 border border-slate-200">
                  {getNodeVisuals(selectedNode).icon}
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-900 font-mono">
                    {selectedNode.id}
                  </h4>
                  <span className="text-[10px] text-slate-500 font-medium">
                    Entity: {selectedNode.type}
                  </span>
                </div>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-400 hover:text-slate-700 p-0.5 rounded"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Properties List */}
            <div className="space-y-1.5 text-[11px]">
              {selectedNode.isFraudRing && (
                <div className="p-1.5 rounded bg-rose-50 border border-rose-200 text-rose-700 font-semibold text-[10px] flex items-center space-x-1">
                  <AlertOctagon className="w-3 h-3 text-rose-600 shrink-0" />
                  <span>Flagged in Coordinated Ring Cluster</span>
                </div>
              )}

              {Object.entries(selectedNode.properties).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between py-0.5 border-b border-slate-50 text-[10.5px]">
                  <span className="text-slate-500 font-medium capitalize">{key.replace('_', ' ')}:</span>
                  <span className="font-mono font-semibold text-slate-800">{String(value)}</span>
                </div>
              ))}
            </div>

            <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-400">
              <span className="font-mono">Graph Node</span>
              <span className="text-indigo-600 font-medium">1-Hop Traversed</span>
            </div>
          </div>
        )}
      </div>

      {/* Legend Footer */}
      <div className="h-8 bg-white border-t border-slate-200 px-4 flex items-center justify-between text-[10px] text-slate-500 shrink-0">
        {nodes.length > 0 ? (
          <div className="flex items-center space-x-3">
            <span className="font-bold text-slate-700 uppercase">Topology Subgraph:</span>
            <span className="flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-slate-800" />
              <span>Transaction</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span>Device</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-purple-500" />
              <span>Card</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-sky-500" />
              <span>Account</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              <span>IP Address</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-rose-500" />
              <span>Prior Case (Memory)</span>
            </span>
          </div>
        ) : (
          <div className="flex items-center space-x-2 text-slate-400">
            <span className="font-bold uppercase">Topology Subgraph:</span>
            <span className="italic">No case selected</span>
          </div>
        )}

        <div className="flex items-center space-x-1.5 text-slate-400">
          <Move className="w-3 h-3" />
          <span>Click & Drag to reposition nodes or pan</span>
        </div>
      </div>
    </div>
  );
};
