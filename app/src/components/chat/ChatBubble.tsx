/**
 * MAGNET UI Module 03: ChatBubble
 *
 * Glass chat bubble with lighting and depth-based blur.
 * Soft streaming caret instead of terminal pipe.
 */

import React from 'react';
import { motion } from 'framer-motion';
import type { ChatBubbleProps } from '../../types/chat';
import { VISIONOS_MOTION } from '../../types/chat';
import styles from './ChatBubble.module.css';

/**
 * Format timestamp to readable time
 */
function formatTime(timestamp: number): string {
  return new Date(timestamp).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

/**
 * Component icon for related component links
 */
const ComponentIcon: React.FC = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
    <path
      d="M6 1L10 3.5V8.5L6 11L2 8.5V3.5L6 1Z"
      stroke="currentColor"
      strokeWidth="1.2"
      strokeLinejoin="round"
    />
  </svg>
);

/**
 * ChatBubble component
 *
 * Glass bubble with lighting gradient and depth-based blur.
 * User messages have accent tint, AI messages are neutral glass.
 */
export const ChatBubble: React.FC<ChatBubbleProps> = ({
  message,
  isLast,
  blurDepth = 0.5,
  onComponentClick,
}) => {
  const isUser = message.role === 'user';
  const isStreaming = message.status === 'streaming';

  // Dynamic blur based on depth (foreground = more blur)
  const dynamicBlur = 16 + blurDepth * 8; // 16-24px

  const bubbleVariants = {
    hidden: {
      opacity: 0,
      y: 12,
      scale: 0.97,
      filter: 'blur(4px)',
    },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      filter: 'blur(0px)',
      transition: {
        type: 'spring',
        ...VISIONOS_MOTION.spring.default,
      },
    },
  };

  return (
    <motion.div
      className={`${styles.wrapper} ${isUser ? styles.user : styles.assistant}`}
      variants={bubbleVariants}
      initial="hidden"
      animate="visible"
      layout
      style={
        {
          '--blur-depth': `${dynamicBlur}px`,
        } as React.CSSProperties
      }
    >
      <div
        className={`${styles.bubble} ${isStreaming ? styles.streaming : ''}`}
      >
        {/* Glass lighting layer */}
        <div className={styles.glassLighting} />

        {/* Content */}
        <div className={styles.content}>
          {message.content}

          {/* Soft streaming caret (not terminal pipe) */}
          {isStreaming && (
            <motion.span
              className={styles.caret}
              animate={{
                opacity: [0.15, 0.6, 0.15],
              }}
              transition={{
                duration: 1.2,
                repeat: Infinity,
                ease: 'easeInOut',
              }}
            />
          )}
        </div>

        {/* Timestamp — very subtle */}
        {!isStreaming && (
          <span className={styles.timestamp}>{formatTime(message.timestamp)}</span>
        )}
      </div>

      {/* Component link */}
      {message.relatedComponentId && onComponentClick && (
        <button
          className={styles.componentLink}
          onClick={() => onComponentClick(message.relatedComponentId!)}
          type="button"
        >
          <ComponentIcon />
          <span>View in workspace</span>
        </button>
      )}
    </motion.div>
  );
};

export default ChatBubble;
