/**
 * MAGNET UI Module 02: ContextMenu
 *
 * 3D-aware context menu with depth transform tied to raycast position.
 * Displays grouped prompts with VisionOS glass material.
 */

import React, { useEffect, useRef, useMemo, useCallback, useState } from 'react';
import type { ContextMenuProps, PRSPrompt, PRSCategory, PRSGroupedPrompts } from '../../../types/prs';
import { getCategoryLabel, hasPrompts } from '../../../types/prs';
import { VisionSurface } from './VisionSurface';
import { ContextMenuItem, ContextMenuGroup } from './ContextMenuItem';
import { PRSIcon } from './icons/PRSIcons';
import styles from './ContextMenu.module.css';

/**
 * Category order for display
 */
const CATEGORY_ORDER: PRSCategory[] = ['action', 'clarification', 'navigation', 'enhancement'];

/**
 * Calculate menu position to stay within viewport
 */
function calculateMenuPosition(
  x: number,
  y: number,
  menuWidth: number,
  menuHeight: number
): { x: number; y: number } {
  const padding = 16;
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;

  let adjustedX = x;
  let adjustedY = y;

  // Check right edge
  if (x + menuWidth + padding > viewportWidth) {
    adjustedX = viewportWidth - menuWidth - padding;
  }

  // Check left edge
  if (adjustedX < padding) {
    adjustedX = padding;
  }

  // Check bottom edge
  if (y + menuHeight + padding > viewportHeight) {
    adjustedY = viewportHeight - menuHeight - padding;
  }

  // Check top edge
  if (adjustedY < padding) {
    adjustedY = padding;
  }

  return { x: adjustedX, y: adjustedY };
}

/**
 * Calculate 3D transform based on world position
 */
function calculate3DTransform(worldPosition?: { x: number; y: number; z: number }): string {
  if (!worldPosition) {
    return 'translateZ(16px) rotateX(0.5deg)';
  }

  // Map world position to subtle rotation
  const rotateX = Math.min(Math.max(worldPosition.y * -0.5, -2), 2);
  const rotateY = Math.min(Math.max(worldPosition.x * 0.5, -2), 2);
  const translateZ = 16 + Math.abs(worldPosition.z) * 2;

  return `translateZ(${translateZ}px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
}

/**
 * ContextMenu component
 */
export const ContextMenu: React.FC<ContextMenuProps> = ({
  isOpen,
  position,
  worldPosition,
  prompts,
  onSelectPrompt,
  onClose,
  targetId,
}) => {
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuDimensions, setMenuDimensions] = useState({ width: 280, height: 200 });
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  // Flatten prompts for keyboard navigation
  const flatPrompts = useMemo(() => {
    const flat: PRSPrompt[] = [];
    for (const category of CATEGORY_ORDER) {
      flat.push(...prompts[category]);
    }
    return flat;
  }, [prompts]);

  // Measure menu dimensions
  useEffect(() => {
    if (isOpen && menuRef.current) {
      const rect = menuRef.current.getBoundingClientRect();
      setMenuDimensions({ width: rect.width, height: rect.height });
    }
  }, [isOpen, prompts]);

  // Calculate adjusted position
  const adjustedPosition = useMemo(() => {
    return calculateMenuPosition(
      position.x,
      position.y,
      menuDimensions.width,
      menuDimensions.height
    );
  }, [position, menuDimensions]);

  // Calculate 3D transform
  const transform3D = useMemo(() => {
    return calculate3DTransform(worldPosition);
  }, [worldPosition]);

  // Handle click outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    // Delay to prevent immediate close
    const timeoutId = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 100);

    return () => {
      clearTimeout(timeoutId);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen, onClose]);

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
        case 'ArrowDown':
          e.preventDefault();
          setHighlightedIndex((prev) =>
            prev < flatPrompts.length - 1 ? prev + 1 : 0
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setHighlightedIndex((prev) =>
            prev > 0 ? prev - 1 : flatPrompts.length - 1
          );
          break;
        case 'Enter':
        case ' ':
          e.preventDefault();
          if (flatPrompts[highlightedIndex]) {
            onSelectPrompt(flatPrompts[highlightedIndex]);
            onClose();
          }
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, flatPrompts, highlightedIndex, onSelectPrompt]);

  // Reset highlighted index when menu opens
  useEffect(() => {
    if (isOpen) {
      setHighlightedIndex(0);
    }
  }, [isOpen]);

  // Handle prompt selection
  const handleSelectPrompt = useCallback(
    (prompt: PRSPrompt) => {
      onSelectPrompt(prompt);
      onClose();
    },
    [onSelectPrompt, onClose]
  );

  // Don't render if not open or no prompts
  if (!isOpen || !hasPrompts(prompts)) {
    return null;
  }

  // Calculate which prompt index corresponds to the highlighted index
  let globalIndex = 0;

  return (
    <div
      className={styles.overlay}
      role="presentation"
    >
      <VisionSurface
        ref={menuRef}
        variant="default"
        depth="near"
        className={styles.menu}
        style={{
          left: adjustedPosition.x,
          top: adjustedPosition.y,
          transform: transform3D,
        }}
        animate={true}
      >
        <div
          className={styles.menuContent}
          role="menu"
          aria-label="Context menu"
          data-target-id={targetId}
        >
          {/* Empty state */}
          {!hasPrompts(prompts) && (
            <div className={styles.empty}>
              <PRSIcon name="info" size={20} />
              <span>No suggestions available</span>
            </div>
          )}

          {/* Render grouped prompts */}
          {CATEGORY_ORDER.map((category) => {
            const categoryPrompts = prompts[category];
            if (categoryPrompts.length === 0) return null;

            const groupStartIndex = globalIndex;

            return (
              <ContextMenuGroup
                key={category}
                category={category}
                label={getCategoryLabel(category)}
              >
                {categoryPrompts.map((prompt, localIndex) => {
                  const currentIndex = groupStartIndex + localIndex;
                  globalIndex++;

                  return (
                    <ContextMenuItem
                      key={prompt.id}
                      prompt={prompt}
                      index={localIndex}
                      onSelect={() => handleSelectPrompt(prompt)}
                      isHighlighted={currentIndex === highlightedIndex}
                    />
                  );
                })}
              </ContextMenuGroup>
            );
          })}
        </div>

        {/* Footer hint */}
        <div className={styles.footer}>
          <span className={styles.hint}>
            <kbd>↑↓</kbd> Navigate • <kbd>↵</kbd> Select • <kbd>Esc</kbd> Close
          </span>
        </div>
      </VisionSurface>
    </div>
  );
};

export default ContextMenu;
