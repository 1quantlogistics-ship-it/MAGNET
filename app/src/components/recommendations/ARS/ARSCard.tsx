/**
 * MAGNET UI ARS Card
 *
 * VisionOS-style recommendation card component.
 * Displays priority, title, impact, and actions for a single recommendation.
 */

import React, { memo, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ARSRecommendation, ARSAction } from '../../../types/ars';
import { VISIONOS_TIMING, type WindowVariant } from '../../../types/common';
import { GlassCard } from '../../core/GlassCard';
import { PillButton } from '../../core/PillButton';
import { PriorityIndicator, getPriorityName } from './icons/PriorityIndicator';
import { ImpactChip, ImpactChips } from './ImpactChip';
import styles from './ARSCard.module.css';

/**
 * ARS Card props
 */
export interface ARSCardProps {
  /** Recommendation data */
  recommendation: ARSRecommendation;
  /** Whether the card is selected */
  isSelected?: boolean;
  /** Whether the card is expanded */
  isExpanded?: boolean;
  /** Click handler */
  onClick?: () => void;
  /** Expand/collapse handler */
  onToggleExpand?: () => void;
  /** Action handler */
  onAction?: (actionId: string) => void;
  /** Navigate to target handler */
  onNavigate?: () => void;
  /** Optional className */
  className?: string;
}

/**
 * Map priority to card variant
 */
function getCardVariant(priority: number): WindowVariant {
  if (priority === 1) return 'critical';
  if (priority === 2) return 'emphasis';
  return 'default';
}

/**
 * ARS Card component
 *
 * @example
 * ```tsx
 * <ARSCard
 *   recommendation={rec}
 *   isSelected={selectedId === rec.id}
 *   isExpanded={expandedId === rec.id}
 *   onClick={() => selectRecommendation(rec.id)}
 *   onToggleExpand={() => toggleExpanded(rec.id)}
 *   onAction={(actionId) => applyAction(rec.id, actionId)}
 * />
 * ```
 */
export const ARSCard = memo<ARSCardProps>(
  ({
    recommendation,
    isSelected = false,
    isExpanded = false,
    onClick,
    onToggleExpand,
    onAction,
    onNavigate,
    className,
  }) => {
    const {
      id,
      priority,
      category,
      title,
      subtitle,
      description,
      impact,
      secondaryImpacts,
      actions,
      targetId,
    } = recommendation;

    // Card variant based on priority
    const variant = useMemo(() => getCardVariant(priority), [priority]);

    // Primary action (first action marked as primary, or first action)
    const primaryAction = useMemo(
      () => actions.find((a) => a.isPrimary) ?? actions[0],
      [actions]
    );

    // Secondary actions
    const secondaryActions = useMemo(
      () => actions.filter((a) => a !== primaryAction),
      [actions, primaryAction]
    );

    // Handle card click
    const handleClick = useCallback(() => {
      onClick?.();
    }, [onClick]);

    // Handle expand toggle
    const handleToggleExpand = useCallback(
      (e: React.MouseEvent) => {
        e.stopPropagation();
        onToggleExpand?.();
      },
      [onToggleExpand]
    );

    // Handle action
    const handleAction = useCallback(
      (action: ARSAction) => (e: React.MouseEvent) => {
        e.stopPropagation();
        if (action.type === 'navigate' && targetId) {
          onNavigate?.();
        } else {
          onAction?.(action.id);
        }
      },
      [onAction, onNavigate, targetId]
    );

    // Animation variants
    const cardVariants = {
      initial: {
        opacity: 0,
        y: 12,
        scale: 0.97,
      },
      animate: {
        opacity: 1,
        y: 0,
        scale: 1,
        transition: {
          type: 'spring',
          stiffness: VISIONOS_TIMING.stiffness,
          damping: VISIONOS_TIMING.damping,
        },
      },
      exit: {
        opacity: 0,
        y: -8,
        scale: 0.98,
        transition: {
          duration: 0.2,
        },
      },
      hover: {
        scale: 1.01,
        transition: {
          type: 'spring',
          stiffness: 400,
          damping: 25,
        },
      },
    };

    const expandedVariants = {
      collapsed: {
        height: 0,
        opacity: 0,
        transition: {
          height: { duration: 0.3, ease: [0.4, 0, 0.2, 1] },
          opacity: { duration: 0.2 },
        },
      },
      expanded: {
        height: 'auto',
        opacity: 1,
        transition: {
          height: { duration: 0.3, ease: [0.4, 0, 0.2, 1] },
          opacity: { duration: 0.2, delay: 0.1 },
        },
      },
    };

    return (
      <GlassCard
        variant={variant}
        size="md"
        elevation={isSelected ? 3 : 2}
        clickable
        isSelected={isSelected}
        onClick={handleClick}
        className={`${styles.card} ${isExpanded ? styles.expanded : ''} ${className ?? ''}`}
        role="article"
        tabIndex={0}
      >
        {/* Header */}
        <div className={styles.header}>
          {/* Priority indicator */}
          <div className={styles.priority}>
            <PriorityIndicator
              priority={priority}
              size={18}
              animated={priority === 1}
            />
            <span className={styles.priorityLabel}>
              {getPriorityName(priority)}
            </span>
          </div>

          {/* Category badge */}
          <span className={styles.category}>{category}</span>
        </div>

        {/* Content */}
        <div className={styles.content}>
          {/* Title */}
          <h3 className={styles.title}>{title}</h3>

          {/* Subtitle */}
          {subtitle && <p className={styles.subtitle}>{subtitle}</p>}

          {/* Impact chips */}
          <div className={styles.impacts}>
            <ImpactChips
              impact={impact}
              secondaryImpacts={secondaryImpacts}
              size="sm"
              maxSecondary={isExpanded ? 3 : 1}
            />
          </div>
        </div>

        {/* Expanded content */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              className={styles.expandedContent}
              variants={expandedVariants}
              initial="collapsed"
              animate="expanded"
              exit="collapsed"
            >
              {/* Description */}
              {description && (
                <p className={styles.description}>{description}</p>
              )}

              {/* Target indicator */}
              {targetId && (
                <button
                  className={styles.targetLink}
                  onClick={(e) => {
                    e.stopPropagation();
                    onNavigate?.();
                  }}
                  type="button"
                >
                  <TargetIcon />
                  <span>View in workspace</span>
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Actions */}
        <div className={styles.actions}>
          {/* Primary action */}
          {primaryAction && (
            <PillButton
              variant="primary"
              size="sm"
              onClick={handleAction(primaryAction)}
              disabled={primaryAction.disabled}
            >
              {primaryAction.label}
            </PillButton>
          )}

          {/* Secondary actions */}
          {secondaryActions.slice(0, 2).map((action) => (
            <PillButton
              key={action.id}
              variant="ghost"
              size="sm"
              onClick={handleAction(action)}
              disabled={action.disabled}
            >
              {action.label}
            </PillButton>
          ))}

          {/* Expand toggle */}
          {(description || (secondaryImpacts && secondaryImpacts.length > 1)) && (
            <button
              className={styles.expandToggle}
              onClick={handleToggleExpand}
              aria-expanded={isExpanded}
              aria-label={isExpanded ? 'Collapse' : 'Expand'}
              type="button"
            >
              <ChevronIcon isExpanded={isExpanded} />
            </button>
          )}
        </div>
      </GlassCard>
    );
  }
);

ARSCard.displayName = 'ARSCard';

/**
 * Target icon component
 */
const TargetIcon: React.FC = () => (
  <svg
    width="12"
    height="12"
    viewBox="0 0 12 12"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.5" />
    <circle cx="6" cy="6" r="2" fill="currentColor" />
  </svg>
);

/**
 * Chevron icon component
 */
const ChevronIcon: React.FC<{ isExpanded: boolean }> = memo(({ isExpanded }) => (
  <motion.svg
    width="16"
    height="16"
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    animate={{ rotate: isExpanded ? 180 : 0 }}
    transition={{ duration: 0.2, ease: 'easeInOut' }}
  >
    <path
      d="M4 6L8 10L12 6"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </motion.svg>
));

ChevronIcon.displayName = 'ChevronIcon';

/**
 * ARS Card skeleton for loading state
 */
export const ARSCardSkeleton: React.FC = memo(() => (
  <div className={styles.skeleton}>
    <div className={styles.skeletonHeader}>
      <div className={styles.skeletonPriority} />
      <div className={styles.skeletonCategory} />
    </div>
    <div className={styles.skeletonContent}>
      <div className={styles.skeletonTitle} />
      <div className={styles.skeletonSubtitle} />
      <div className={styles.skeletonChip} />
    </div>
    <div className={styles.skeletonActions}>
      <div className={styles.skeletonButton} />
      <div className={styles.skeletonButton} />
    </div>
  </div>
));

ARSCardSkeleton.displayName = 'ARSCardSkeleton';

export default ARSCard;
