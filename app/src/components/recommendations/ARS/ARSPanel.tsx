/**
 * MAGNET UI ARS Panel
 *
 * VisionOS-style floating panel for displaying ARS recommendations.
 * Features soft focus, glass morphism, and staggered card animations.
 */

import React, { memo, useCallback, useMemo, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ARSRecommendation, ARSCategory, ARSPriority } from '../../../types/ars';
import { VISIONOS_TIMING } from '../../../types/common';
import { FloatingMicroWindow } from '../../core/FloatingMicroWindow';
import { useSoftFocus } from '../../../hooks/useSoftFocus';
import { ARSCard, ARSCardSkeleton } from './ARSCard';
import { TelemetryStrip } from './TelemetryStrip';
import {
  arsStore,
  selectRecommendation,
  toggleRecommendationExpansion,
  getFilteredRecommendations,
  setFilterCategory,
  setFilterPriority,
  clearFilters,
} from '../../../stores/domain/arsStore';
import styles from './ARSPanel.module.css';

/**
 * ARS Panel props
 */
export interface ARSPanelProps {
  /** Initial position */
  position?: { x: number; y: number };
  /** Whether panel is collapsed */
  isCollapsed?: boolean;
  /** Toggle collapsed state */
  onToggleCollapsed?: () => void;
  /** Optional className */
  className?: string;
}

/**
 * Category filter options
 */
const CATEGORY_OPTIONS: Array<{ value: ARSCategory | 'all'; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 'stability', label: 'Stability' },
  { value: 'structure', label: 'Structure' },
  { value: 'propulsion', label: 'Propulsion' },
  { value: 'systems', label: 'Systems' },
  { value: 'compliance', label: 'Compliance' },
  { value: 'optimization', label: 'Optimization' },
];

/**
 * Priority filter options
 */
const PRIORITY_OPTIONS: Array<{ value: ARSPriority | 'all'; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 1, label: 'Critical' },
  { value: 2, label: 'High' },
  { value: 3, label: 'Medium' },
  { value: 4, label: 'Low' },
  { value: 5, label: 'Info' },
];

/**
 * ARS Panel component
 *
 * @example
 * ```tsx
 * <ARSPanel
 *   position={{ x: 20, y: 80 }}
 *   isCollapsed={false}
 *   onToggleCollapsed={() => setCollapsed((c) => !c)}
 * />
 * ```
 */
export const ARSPanel = memo<ARSPanelProps>(
  ({
    position = { x: 20, y: 80 },
    isCollapsed = false,
    onToggleCollapsed,
    className,
  }) => {
    // Store subscription
    const [storeState, setStoreState] = useState(() => arsStore.getState());

    useEffect(() => {
      const unsubscribe = arsStore.subscribe(setStoreState);
      return unsubscribe;
    }, []);

    // Soft focus management
    const focus = useSoftFocus({
      panelId: 'inspector',
      depth: 'mid',
      focusOnHover: true,
      focusOnClick: true,
    });

    // Get filtered recommendations
    const recommendations = useMemo(
      () => getFilteredRecommendations(),
      [storeState.readOnly.recommendations, storeState.readOnly.filterCategory, storeState.readOnly.filterPriority]
    );

    // Current telemetry item
    const currentTelemetryItem = useMemo(() => {
      const { currentTelemetryId, recommendations } = storeState.readOnly;
      if (!currentTelemetryId) return null;
      return recommendations.find((r) => r.id === currentTelemetryId) ?? null;
    }, [storeState.readOnly]);

    // Telemetry queue length
    const telemetryQueueLength = useMemo(
      () => (storeState.readOnly.telemetryQueue?.length ?? 0),
      [storeState.readOnly]
    );

    // Selected and expanded states
    const selectedId = storeState.readOnly.selectedRecommendationId;
    const expandedIds = storeState.readOnly.expandedRecommendationIds;

    // Loading state
    const isLoading = storeState.readOnly.isLoading;

    // Filter states
    const activeCategory = storeState.readOnly.filterCategory;
    const activePriority = storeState.readOnly.filterPriority;

    // Handlers
    const handleSelectRecommendation = useCallback((id: string) => {
      selectRecommendation(id);
    }, []);

    const handleToggleExpand = useCallback((id: string) => {
      toggleRecommendationExpansion(id);
    }, []);

    const handleCategoryFilter = useCallback((category: ARSCategory | 'all') => {
      setFilterCategory(category === 'all' ? null : category);
    }, []);

    const handlePriorityFilter = useCallback((priority: ARSPriority | 'all') => {
      setFilterPriority(priority === 'all' ? null : priority);
    }, []);

    const handleClearFilters = useCallback(() => {
      clearFilters();
    }, []);

    const handleTelemetryDismiss = useCallback(() => {
      // Dismiss current telemetry - show next in queue
      arsStore.getState()._update((state) => {
        const nextId = state.telemetryQueue?.[0] ?? null;
        return {
          currentTelemetryId: nextId,
          telemetryQueue: state.telemetryQueue?.slice(1) ?? [],
        };
      });
    }, []);

    const handleTelemetryView = useCallback(() => {
      if (currentTelemetryItem) {
        selectRecommendation(currentTelemetryItem.id);
      }
    }, [currentTelemetryItem]);

    // Animation variants
    const panelVariants = {
      collapsed: {
        width: 48,
        height: 48,
        transition: {
          type: 'spring',
          stiffness: VISIONOS_TIMING.stiffness,
          damping: VISIONOS_TIMING.damping,
        },
      },
      expanded: {
        width: 380,
        height: 'auto',
        transition: {
          type: 'spring',
          stiffness: VISIONOS_TIMING.stiffness,
          damping: VISIONOS_TIMING.damping,
        },
      },
    };

    const listVariants = {
      hidden: { opacity: 0 },
      visible: {
        opacity: 1,
        transition: {
          staggerChildren: 0.05,
          delayChildren: 0.1,
        },
      },
    };

    const itemVariants = {
      hidden: { opacity: 0, y: 12 },
      visible: {
        opacity: 1,
        y: 0,
        transition: {
          type: 'spring',
          stiffness: VISIONOS_TIMING.stiffness,
          damping: VISIONOS_TIMING.damping,
        },
      },
    };

    // Has active filters
    const hasActiveFilters = activeCategory !== null || activePriority !== null;

    return (
      <>
        {/* Telemetry strip for high-priority alerts */}
        <TelemetryStrip
          recommendation={currentTelemetryItem}
          queueLength={telemetryQueueLength}
          autoDismissMs={15000}
          onDismiss={handleTelemetryDismiss}
          onView={handleTelemetryView}
        />

        {/* Main panel */}
        <motion.div
          className={`${styles.panelContainer} ${className ?? ''}`}
          style={{ left: position.x, top: position.y }}
          variants={panelVariants}
          animate={isCollapsed ? 'collapsed' : 'expanded'}
          {...focus.handlers}
        >
          <FloatingMicroWindow
            panelId="inspector"
            depth="mid"
            variant="default"
            isVisible={true}
            enableGlass={true}
            enableGlow={true}
            enableShadow={true}
            enableFocus={true}
            className={styles.panel}
          >
            {/* Collapsed state - just icon */}
            {isCollapsed ? (
              <button
                className={styles.collapseToggle}
                onClick={onToggleCollapsed}
                aria-label="Expand recommendations panel"
                type="button"
              >
                <RecommendationsIcon />
                {recommendations.length > 0 && (
                  <span className={styles.badge}>{recommendations.length}</span>
                )}
              </button>
            ) : (
              <>
                {/* Header */}
                <div className={styles.header}>
                  <h2 className={styles.title}>Recommendations</h2>
                  <div className={styles.headerActions}>
                    <span className={styles.count}>
                      {recommendations.length} active
                    </span>
                    <button
                      className={styles.collapseButton}
                      onClick={onToggleCollapsed}
                      aria-label="Collapse panel"
                      type="button"
                    >
                      <CollapseIcon />
                    </button>
                  </div>
                </div>

                {/* Filters */}
                <div className={styles.filters}>
                  {/* Category filter */}
                  <div className={styles.filterGroup}>
                    <label className={styles.filterLabel}>Category</label>
                    <div className={styles.filterOptions}>
                      {CATEGORY_OPTIONS.slice(0, 4).map((opt) => (
                        <button
                          key={opt.value}
                          className={`${styles.filterChip} ${
                            (opt.value === 'all' && !activeCategory) ||
                            activeCategory === opt.value
                              ? styles.active
                              : ''
                          }`}
                          onClick={() => handleCategoryFilter(opt.value)}
                          type="button"
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Priority filter */}
                  <div className={styles.filterGroup}>
                    <label className={styles.filterLabel}>Priority</label>
                    <div className={styles.filterOptions}>
                      {PRIORITY_OPTIONS.slice(0, 4).map((opt) => (
                        <button
                          key={opt.value}
                          className={`${styles.filterChip} ${
                            (opt.value === 'all' && !activePriority) ||
                            activePriority === opt.value
                              ? styles.active
                              : ''
                          }`}
                          onClick={() => handlePriorityFilter(opt.value)}
                          type="button"
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Clear filters */}
                  {hasActiveFilters && (
                    <button
                      className={styles.clearFilters}
                      onClick={handleClearFilters}
                      type="button"
                    >
                      Clear filters
                    </button>
                  )}
                </div>

                {/* Recommendations list */}
                <div className={styles.list}>
                  {isLoading ? (
                    // Loading skeletons
                    <div className={styles.skeletons}>
                      {[1, 2, 3].map((i) => (
                        <ARSCardSkeleton key={i} />
                      ))}
                    </div>
                  ) : recommendations.length === 0 ? (
                    // Empty state
                    <div className={styles.empty}>
                      <EmptyIcon />
                      <p>No recommendations</p>
                      {hasActiveFilters && (
                        <button
                          className={styles.clearFiltersSmall}
                          onClick={handleClearFilters}
                          type="button"
                        >
                          Clear filters
                        </button>
                      )}
                    </div>
                  ) : (
                    // Recommendations
                    <motion.div
                      variants={listVariants}
                      initial="hidden"
                      animate="visible"
                    >
                      <AnimatePresence mode="popLayout">
                        {recommendations.map((rec) => (
                          <motion.div
                            key={rec.id}
                            variants={itemVariants}
                            layout
                          >
                            <ARSCard
                              recommendation={rec}
                              isSelected={selectedId === rec.id}
                              isExpanded={expandedIds?.includes(rec.id) ?? false}
                              onClick={() => handleSelectRecommendation(rec.id)}
                              onToggleExpand={() => handleToggleExpand(rec.id)}
                              onAction={(actionId) => {
                                // Handle action
                                console.log('Action:', actionId, 'on', rec.id);
                              }}
                              onNavigate={() => {
                                // Navigate to target
                                console.log('Navigate to:', rec.targetId);
                              }}
                            />
                          </motion.div>
                        ))}
                      </AnimatePresence>
                    </motion.div>
                  )}
                </div>
              </>
            )}
          </FloatingMicroWindow>
        </motion.div>
      </>
    );
  }
);

ARSPanel.displayName = 'ARSPanel';

/**
 * Recommendations icon
 */
const RecommendationsIcon: React.FC = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 20 20"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M10 2L2 6V14L10 18L18 14V6L10 2Z"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinejoin="round"
    />
    <path
      d="M10 9V13M10 6V7"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
    />
  </svg>
);

/**
 * Collapse icon
 */
const CollapseIcon: React.FC = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M4 6L8 10L12 6"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

/**
 * Empty state icon
 */
const EmptyIcon: React.FC = () => (
  <svg
    width="48"
    height="48"
    viewBox="0 0 48 48"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <circle
      cx="24"
      cy="24"
      r="20"
      stroke="currentColor"
      strokeWidth="2"
      strokeDasharray="4 4"
      opacity="0.3"
    />
    <path
      d="M24 16V28M24 32V34"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      opacity="0.5"
    />
  </svg>
);

export default ARSPanel;
