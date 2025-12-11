/**
 * MAGNET UI Module 03: useEdgeResize Hook
 *
 * Edge-hover resize detection for frameless windows.
 * Invisible handles with edge glow affordance.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import type { ResizeEdge, ResizeConstraints, ChatWindowSize } from '../types/chat';

/**
 * Edge resize hook options
 */
export interface EdgeResizeOptions {
  /** Whether resize is enabled */
  enabled: boolean;
  /** Edge detection threshold in pixels */
  edgeThreshold?: number;
  /** Resize constraints */
  constraints?: ResizeConstraints;
  /** Callback when size changes */
  onResize: (size: ChatWindowSize) => void;
}

/**
 * Edge resize hook return value
 */
export interface EdgeResizeResult {
  /** Currently hovered edge */
  edgeHover: ResizeEdge;
  /** Whether currently resizing */
  isResizing: boolean;
  /** Cursor style to apply */
  cursorStyle: string;
  /** Mouse move handler for edge detection */
  handleMouseMove: (e: React.MouseEvent<HTMLElement>) => void;
  /** Mouse down handler to start resize */
  handleResizeStart: (e: React.MouseEvent<HTMLElement>) => void;
  /** Reset edge hover state */
  resetEdgeHover: () => void;
}

/**
 * Default resize constraints
 */
const DEFAULT_CONSTRAINTS: ResizeConstraints = {
  minWidth: 360,
  maxWidth: 560,
  minHeight: 400,
  maxHeight: 800,
};

/**
 * Edge resize hook for frameless windows
 *
 * Detects edge hover for invisible resize handles,
 * provides cursor styling and resize behavior.
 *
 * @example
 * ```tsx
 * const {
 *   edgeHover,
 *   cursorStyle,
 *   handleMouseMove,
 *   handleResizeStart
 * } = useEdgeResize({
 *   enabled: windowState === 'expanded',
 *   onResize: setSize
 * });
 *
 * return (
 *   <div
 *     style={{ cursor: cursorStyle }}
 *     onMouseMove={handleMouseMove}
 *     onMouseDown={handleResizeStart}
 *   >
 *     {edgeHover && <div className={`edge-glow ${edgeHover}`} />}
 *   </div>
 * );
 * ```
 */
export function useEdgeResize({
  enabled,
  edgeThreshold = 12,
  constraints = DEFAULT_CONSTRAINTS,
  onResize,
}: EdgeResizeOptions): EdgeResizeResult {
  const [edgeHover, setEdgeHover] = useState<ResizeEdge>(null);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeEdge, setResizeEdge] = useState<ResizeEdge>(null);

  const startRef = useRef({
    x: 0,
    y: 0,
    width: 0,
    height: 0,
  });

  /**
   * Detect which edge the cursor is near
   */
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLElement>) => {
      if (!enabled || isResizing) return;

      const rect = e.currentTarget.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const nearRight = rect.width - x < edgeThreshold;
      const nearBottom = rect.height - y < edgeThreshold;

      if (nearRight && nearBottom) {
        setEdgeHover('corner');
      } else if (nearRight) {
        setEdgeHover('right');
      } else if (nearBottom) {
        setEdgeHover('bottom');
      } else {
        setEdgeHover(null);
      }
    },
    [enabled, isResizing, edgeThreshold]
  );

  /**
   * Start resize on mousedown at edge
   */
  const handleResizeStart = useCallback(
    (e: React.MouseEvent<HTMLElement>) => {
      if (!edgeHover || !enabled) return;

      e.preventDefault();
      e.stopPropagation();

      const rect = e.currentTarget.getBoundingClientRect();
      startRef.current = {
        x: e.clientX,
        y: e.clientY,
        width: rect.width,
        height: rect.height,
      };

      setIsResizing(true);
      setResizeEdge(edgeHover);
    },
    [edgeHover, enabled]
  );

  /**
   * Reset edge hover state
   */
  const resetEdgeHover = useCallback(() => {
    setEdgeHover(null);
  }, []);

  /**
   * Handle resize move and end
   */
  useEffect(() => {
    if (!isResizing || !resizeEdge) return;

    const handleMove = (e: MouseEvent) => {
      const deltaX = e.clientX - startRef.current.x;
      const deltaY = e.clientY - startRef.current.y;

      let newWidth = startRef.current.width;
      let newHeight = startRef.current.height;

      // Calculate new dimensions based on which edge is being dragged
      if (resizeEdge === 'right' || resizeEdge === 'corner') {
        newWidth = Math.min(
          constraints.maxWidth,
          Math.max(constraints.minWidth, startRef.current.width + deltaX)
        );
      }

      if (resizeEdge === 'bottom' || resizeEdge === 'corner') {
        newHeight = Math.min(
          constraints.maxHeight,
          Math.max(constraints.minHeight, startRef.current.height + deltaY)
        );
      }

      onResize({ width: newWidth, height: newHeight });
    };

    const handleUp = () => {
      setIsResizing(false);
      setResizeEdge(null);
    };

    // Add listeners to document for resize tracking
    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleUp);

    // Prevent text selection during resize
    document.body.style.userSelect = 'none';
    document.body.style.cursor = getCursorStyle(resizeEdge);

    return () => {
      document.removeEventListener('mousemove', handleMove);
      document.removeEventListener('mouseup', handleUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isResizing, resizeEdge, constraints, onResize]);

  /**
   * Get cursor style based on edge
   */
  const cursorStyle = getCursorStyle(edgeHover);

  return {
    edgeHover,
    isResizing,
    cursorStyle,
    handleMouseMove,
    handleResizeStart,
    resetEdgeHover,
  };
}

/**
 * Get CSS cursor style for edge
 */
function getCursorStyle(edge: ResizeEdge): string {
  switch (edge) {
    case 'corner':
      return 'nwse-resize';
    case 'right':
      return 'ew-resize';
    case 'bottom':
      return 'ns-resize';
    default:
      return 'grab';
  }
}

export default useEdgeResize;
