/**
 * MAGNET UI Module 03: ChatInput
 *
 * Soft floating input with no visible border.
 * Auto-resize textarea with context indicator.
 */

import React, { useRef, useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ChatInputProps } from '../../types/chat';
import { useChatStore } from '../../stores/domain/chatStore';
import styles from './ChatInput.module.css';

/**
 * Send icon
 */
const SendIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path
      d="M3 8H13M13 8L9 4M13 8L9 12"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

/**
 * Stop icon
 */
const StopIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <rect x="4" y="4" width="8" height="8" rx="1" fill="currentColor" />
  </svg>
);

/**
 * Context icon (hexagon)
 */
const ContextIcon: React.FC = () => (
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
 * Close icon
 */
const CloseIcon: React.FC = () => (
  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
    <path
      d="M2 2L8 8M8 2L2 8"
      stroke="currentColor"
      strokeWidth="1.2"
      strokeLinecap="round"
    />
  </svg>
);

/**
 * ChatInput component
 *
 * Soft floating input with auto-resize and context indicator.
 */
export const ChatInput: React.FC<ChatInputProps> = ({
  placeholder = 'Ask MAGNET AI...',
  disabled = false,
  maxLength = 4000,
  onSubmit,
}) => {
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const [isFocused, setIsFocused] = useState(false);

  const {
    inputValue,
    setInputValue,
    isStreaming,
    sendMessage,
    cancelStreaming,
    context,
    clearContext,
  } = useChatStore();

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 100)}px`;
    }
  }, [inputValue]);

  // Handle submit
  const handleSubmit = useCallback(() => {
    if (!inputValue.trim() || isStreaming || disabled) return;

    const content = inputValue.trim();

    if (onSubmit) {
      onSubmit(content);
    } else {
      sendMessage(content);
    }

    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }
  }, [inputValue, isStreaming, disabled, onSubmit, sendMessage]);

  // Handle key down
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Handle stop streaming
  const handleStop = useCallback(() => {
    cancelStreaming();
  }, [cancelStreaming]);

  const hasContext = context.componentId !== null;
  const canSubmit = inputValue.trim().length > 0 && !isStreaming && !disabled;

  return (
    <div className={styles.container}>
      {/* Context indicator */}
      <AnimatePresence>
        {hasContext && (
          <motion.div
            className={styles.context}
            initial={{ opacity: 0, height: 0, marginBottom: 0 }}
            animate={{ opacity: 1, height: 'auto', marginBottom: 12 }}
            exit={{ opacity: 0, height: 0, marginBottom: 0 }}
          >
            <ContextIcon />
            <span>{context.label || 'Discussing selected component'}</span>
            <button onClick={clearContext} type="button">
              <CloseIcon />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input — NO visible border */}
      <div
        className={`${styles.inputWrapper} ${isFocused ? styles.focused : ''}`}
      >
        <textarea
          ref={inputRef}
          className={styles.input}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={1}
          disabled={isStreaming || disabled}
          maxLength={maxLength}
        />

        <motion.button
          className={styles.sendButton}
          onClick={isStreaming ? handleStop : handleSubmit}
          disabled={!isStreaming && !canSubmit}
          whileHover={{ scale: 1.06 }}
          whileTap={{ scale: 0.94 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }}
          type="button"
        >
          {isStreaming ? <StopIcon /> : <SendIcon />}
        </motion.button>
      </div>
    </div>
  );
};

export default ChatInput;
