/**
 * MAGNET UI Module 04: ClarificationManager
 *
 * Orchestrator component that renders the appropriate clarification UI
 * based on the active request type.
 */

import React from 'react';
import { AnimatePresence } from 'framer-motion';
import type { ClarificationRequest } from '../../types/clarification';

// Note: These components will be implemented by Bravo agent
// Importing from placeholders for now
// import { QuickClarification } from './QuickClarification';
// import { StandardClarification } from './StandardClarification';
// import { ComplexClarification } from './ComplexClarification';
// import { ContextualPrompt } from './ContextualPrompt';

/**
 * ClarificationManager props
 */
export interface ClarificationManagerProps {
  /** Currently active clarification request */
  activeRequest: ClarificationRequest | null;
  /** Handler for responding to clarification */
  onRespond: (requestId: string, response: unknown) => void;
  /** Handler for skipping clarification */
  onSkip: (requestId: string) => void;
}

/**
 * Placeholder component for clarifications not yet implemented
 * These will be replaced by Bravo agent implementations
 */
const PlaceholderClarification: React.FC<{
  request: ClarificationRequest;
  onRespond: (response: unknown) => void;
  onSkip: () => void;
}> = ({ request, onRespond, onSkip }) => (
  <div
    style={{
      position: 'fixed',
      top: '50%',
      left: '50%',
      transform: 'translate(-50%, -50%)',
      padding: '24px',
      background: 'rgba(30, 32, 38, 0.95)',
      backdropFilter: 'blur(24px)',
      borderRadius: '20px',
      color: '#fff',
      zIndex: 1001,
    }}
  >
    <p style={{ margin: '0 0 12px 0', opacity: 0.7 }}>
      [{request.type.toUpperCase()} CLARIFICATION]
    </p>
    <p style={{ margin: '0 0 16px 0' }}>{request.question}</p>
    <div style={{ display: 'flex', gap: '12px' }}>
      <button
        onClick={() => onRespond(request.defaultValue)}
        style={{
          padding: '8px 16px',
          background: 'rgba(126, 184, 231, 0.2)',
          border: 'none',
          borderRadius: '8px',
          color: '#7EB8E7',
          cursor: 'pointer',
        }}
      >
        Accept Default
      </button>
      <button
        onClick={onSkip}
        style={{
          padding: '8px 16px',
          background: 'rgba(255, 255, 255, 0.05)',
          border: 'none',
          borderRadius: '8px',
          color: '#9BA3B0',
          cursor: 'pointer',
        }}
      >
        Skip
      </button>
    </div>
  </div>
);

/**
 * ClarificationManager component
 *
 * Routes to the appropriate clarification component based on request type.
 */
export const ClarificationManager: React.FC<ClarificationManagerProps> = ({
  activeRequest,
  onRespond,
  onSkip,
}) => {
  if (!activeRequest) {
    return null;
  }

  const handleRespond = (response: unknown) => {
    onRespond(activeRequest.id, response);
  };

  const handleSkip = () => {
    onSkip(activeRequest.id);
  };

  // Render appropriate component based on type
  // Note: Replace placeholders with actual components when Bravo implements them
  const renderClarification = () => {
    switch (activeRequest.type) {
      case 'quick':
        // return <QuickClarification request={activeRequest} />;
        return (
          <PlaceholderClarification
            request={activeRequest}
            onRespond={handleRespond}
            onSkip={handleSkip}
          />
        );

      case 'standard':
        // return <StandardClarification request={activeRequest} />;
        return (
          <PlaceholderClarification
            request={activeRequest}
            onRespond={handleRespond}
            onSkip={handleSkip}
          />
        );

      case 'complex':
        // return <ComplexClarification request={activeRequest} />;
        return (
          <PlaceholderClarification
            request={activeRequest}
            onRespond={handleRespond}
            onSkip={handleSkip}
          />
        );

      case 'contextual':
        // return <ContextualPrompt request={activeRequest} />;
        return (
          <PlaceholderClarification
            request={activeRequest}
            onRespond={handleRespond}
            onSkip={handleSkip}
          />
        );

      default:
        return null;
    }
  };

  return <AnimatePresence mode="wait">{renderClarification()}</AnimatePresence>;
};

export default ClarificationManager;
