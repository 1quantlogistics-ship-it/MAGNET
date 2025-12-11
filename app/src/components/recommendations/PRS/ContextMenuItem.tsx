/**
 * MAGNET UI Module 02: ContextMenuItem
 *
 * Individual menu item for the PRS context menu.
 * Displays prompt with icon, label, and category indicator.
 */

import React, { useMemo, useCallback } from 'react';
import type { ContextMenuItemProps, PRSCategory } from '../../../types/prs';
import { PRSIcon } from './icons/PRSIcons';
import styles from './ContextMenuItem.module.css';

/**
 * Get category indicator color
 */
function getCategoryColor(category: PRSCategory): string {
  const colors: Record<PRSCategory, string> = {
    action: 'var(--prs-category-action)',
    clarification: 'var(--prs-category-clarification)',
    navigation: 'var(--prs-category-navigation)',
    enhancement: 'var(--prs-category-enhancement)',
  };
  return colors[category];
}

/**
 * ContextMenuItem component
 */
export const ContextMenuItem: React.FC<ContextMenuItemProps> = ({
  prompt,
  index,
  onSelect,
  isHighlighted = false,
}) => {
  // Category class for styling
  const categoryClass = useMemo(() => {
    switch (prompt.category) {
      case 'action':
        return styles.categoryAction;
      case 'clarification':
        return styles.categoryClarification;
      case 'navigation':
        return styles.categoryNavigation;
      case 'enhancement':
        return styles.categoryEnhancement;
      default:
        return '';
    }
  }, [prompt.category]);

  // Handle click
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      onSelect();
    },
    [onSelect]
  );

  // Handle keyboard
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onSelect();
      }
    },
    [onSelect]
  );

  // Animation delay based on index
  const animationStyle = useMemo(
    () => ({
      animationDelay: `${index * 50}ms`,
    }),
    [index]
  );

  return (
    <button
      className={`
        ${styles.item}
        ${categoryClass}
        ${isHighlighted ? styles.highlighted : ''}
      `}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      style={animationStyle}
      role="menuitem"
      tabIndex={0}
      data-category={prompt.category}
      data-index={index}
    >
      {/* Category indicator bar */}
      <div
        className={styles.categoryIndicator}
        style={{ backgroundColor: getCategoryColor(prompt.category) }}
        aria-hidden="true"
      />

      {/* Icon */}
      <span className={styles.icon}>
        <PRSIcon name={prompt.icon as any} size={16} />
      </span>

      {/* Label */}
      <span className={styles.label}>{prompt.label}</span>

      {/* Action indicator */}
      <span className={styles.actionIndicator}>
        <PRSIcon name="chevron-right" size={12} />
      </span>
    </button>
  );
};

/**
 * ContextMenuDivider - Visual separator between groups
 */
export const ContextMenuDivider: React.FC<{ label?: string }> = ({ label }) => {
  return (
    <div className={styles.divider} role="separator">
      {label && <span className={styles.dividerLabel}>{label}</span>}
    </div>
  );
};

/**
 * ContextMenuGroup - Groups items with optional header
 */
export const ContextMenuGroup: React.FC<{
  category: PRSCategory;
  label: string;
  children: React.ReactNode;
}> = ({ category, label, children }) => {
  return (
    <div className={styles.group} role="group" aria-label={label}>
      <div className={styles.groupHeader}>
        <span className={styles.groupLabel}>{label}</span>
      </div>
      <div className={styles.groupItems}>{children}</div>
    </div>
  );
};

export default ContextMenuItem;
