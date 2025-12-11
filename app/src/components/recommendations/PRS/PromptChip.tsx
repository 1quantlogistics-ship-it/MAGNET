/**
 * MAGNET UI Module 02: PromptChip
 *
 * Chat suggestion chip component with VisionOS pill styling.
 * Displays above the chat input as contextual quick-actions.
 */

import React, { useCallback } from 'react';
import type { PRSPrompt, PRSCategory } from '../../../types/prs';
import { PRSIcon, getCategoryIconName } from './icons/PRSIcons';
import styles from './PromptChip.module.css';

/**
 * PromptChip props
 */
export interface PromptChipProps {
  /** Prompt data */
  prompt: PRSPrompt;
  /** Selection handler */
  onSelect: (prompt: PRSPrompt) => void;
  /** Optional size variant */
  size?: 'sm' | 'md';
  /** Show category icon */
  showIcon?: boolean;
  /** Animation delay for stagger effect */
  animationDelay?: number;
}

/**
 * PromptChip component
 */
export const PromptChip: React.FC<PromptChipProps> = ({
  prompt,
  onSelect,
  size = 'md',
  showIcon = true,
  animationDelay = 0,
}) => {
  const handleClick = useCallback(() => {
    onSelect(prompt);
  }, [prompt, onSelect]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onSelect(prompt);
      }
    },
    [prompt, onSelect]
  );

  return (
    <button
      className={`${styles.chip} ${styles[`size${size.charAt(0).toUpperCase()}${size.slice(1)}`]}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      type="button"
      role="option"
      aria-label={prompt.label}
      data-category={prompt.category}
      style={{
        animationDelay: `${animationDelay}ms`,
      }}
    >
      {showIcon && (
        <span className={styles.icon}>
          <PRSIcon
            name={getCategoryIconName(prompt.category)}
            size={size === 'sm' ? 12 : 14}
          />
        </span>
      )}
      <span className={styles.label}>{prompt.label}</span>
    </button>
  );
};

/**
 * PromptChipGroup props
 */
export interface PromptChipGroupProps {
  /** Array of prompts to display */
  prompts: PRSPrompt[];
  /** Selection handler */
  onSelect: (prompt: PRSPrompt) => void;
  /** Maximum chips to show */
  maxVisible?: number;
  /** Chip size */
  size?: 'sm' | 'md';
  /** Show category icons */
  showIcons?: boolean;
  /** Additional class name */
  className?: string;
}

/**
 * PromptChipGroup component
 * Container for multiple chips with stagger animation
 */
export const PromptChipGroup: React.FC<PromptChipGroupProps> = ({
  prompts,
  onSelect,
  maxVisible = 4,
  size = 'md',
  showIcons = true,
  className,
}) => {
  const visiblePrompts = prompts.slice(0, maxVisible);
  const hiddenCount = prompts.length - maxVisible;

  if (visiblePrompts.length === 0) {
    return null;
  }

  return (
    <div
      className={`${styles.chipGroup} ${className || ''}`}
      role="listbox"
      aria-label="Suggested prompts"
    >
      {visiblePrompts.map((prompt, index) => (
        <PromptChip
          key={prompt.id}
          prompt={prompt}
          onSelect={onSelect}
          size={size}
          showIcon={showIcons}
          animationDelay={index * 50}
        />
      ))}
      {hiddenCount > 0 && (
        <span className={styles.moreIndicator}>
          +{hiddenCount} more
        </span>
      )}
    </div>
  );
};

export default PromptChip;
