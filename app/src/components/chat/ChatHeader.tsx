/**
 * MAGNET UI Module 03: ChatHeader
 *
 * Minimal chrome header with AI presence orb.
 * Drag handle for window repositioning.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { AIPresenceOrb } from './AIPresenceOrb';
import { useChatStore } from '../../stores/domain/chatStore';
import type { ChatHeaderProps } from '../../types/chat';
import styles from './ChatHeader.module.css';

/**
 * Header icon component
 */
const HeaderIcon: React.FC<{ name: string }> = ({ name }) => {
  switch (name) {
    case 'minimize':
      return (
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path
            d="M3 7H11"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      );
    case 'expand':
      return (
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <rect
            x="2"
            y="2"
            width="10"
            height="10"
            rx="2"
            stroke="currentColor"
            strokeWidth="1.5"
          />
        </svg>
      );
    case 'collapse':
      return (
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <rect
            x="3"
            y="3"
            width="8"
            height="8"
            rx="1.5"
            stroke="currentColor"
            strokeWidth="1.5"
          />
        </svg>
      );
    case 'undock':
      return (
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <rect
            x="4"
            y="2"
            width="8"
            height="10"
            rx="1.5"
            stroke="currentColor"
            strokeWidth="1.5"
          />
          <path
            d="M4 7H1M1 7L2.5 5.5M1 7L2.5 8.5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      );
    default:
      return null;
  }
};

/**
 * Header button component
 */
const HeaderButton: React.FC<{
  icon: string;
  onClick: () => void;
  'aria-label': string;
}> = ({ icon, onClick, 'aria-label': ariaLabel }) => (
  <motion.button
    className={styles.button}
    onClick={(e) => {
      e.stopPropagation();
      onClick();
    }}
    whileHover={{
      scale: 1.1,
      backgroundColor: 'rgba(255, 255, 255, 0.06)',
    }}
    whileTap={{ scale: 0.95 }}
    transition={{
      type: 'spring',
      stiffness: 400,
      damping: 25,
    }}
    type="button"
    aria-label={ariaLabel}
  >
    <HeaderIcon name={icon} />
  </motion.button>
);

/**
 * ChatHeader component
 *
 * Minimal header with AI presence orb and window controls.
 */
export const ChatHeader: React.FC<ChatHeaderProps> = ({
  windowState,
  onDragStart,
  onMinimize,
  onMaximize,
  onUndock,
}) => {
  const { isStreaming } = useChatStore();

  return (
    <div
      className={styles.header}
      onPointerDown={windowState === 'expanded' ? onDragStart : undefined}
    >
      {/* AI presence */}
      <div className={styles.presence}>
        <AIPresenceOrb isStreaming={isStreaming} size="md" />
        <span className={styles.title}>MAGNET AI</span>
      </div>

      {/* Window controls — minimal, no borders */}
      <div className={styles.controls}>
        {windowState === 'docked' && (
          <HeaderButton icon="undock" onClick={onUndock} aria-label="Undock window" />
        )}
        <HeaderButton
          icon={windowState === 'fullscreen' ? 'collapse' : 'expand'}
          onClick={onMaximize}
          aria-label={windowState === 'fullscreen' ? 'Exit fullscreen' : 'Enter fullscreen'}
        />
        <HeaderButton icon="minimize" onClick={onMinimize} aria-label="Minimize window" />
      </div>
    </div>
  );
};

export default ChatHeader;
