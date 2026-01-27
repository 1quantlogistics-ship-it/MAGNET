/**
 * MAGNET App - Main Application Component
 *
 * Composes the VisionOS-style UI components into the main ship design interface.
 * Wired to Control Plane v1.1 via useChat hook.
 */

import React, { useCallback, useEffect } from 'react';
import { FloatingMicroWindow } from './components/core/FloatingMicroWindow';
import { OrbPresence } from './components/core/OrbPresence';
import { PillButton } from './components/core/PillButton';
import { AIPresenceOrb } from './components/chat/AIPresenceOrb';
import { ChatBubble } from './components/chat/ChatBubble';
import { ChatInput } from './components/chat/ChatInput';
import { PhaseProgress } from './components/prs/PhaseProgress';
import { SpatialOcclusionProvider } from './contexts/SpatialOcclusionContext';
import { useChat } from './hooks/useChat';
import { usePRSStore, setDesignId } from './stores/domain/prsStore';
import { useChatStore } from './stores/domain/chatStore';

// Inline styles for the app shell
const appStyles: React.CSSProperties = {
  minHeight: '100vh',
  background: 'linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0f0f1a 100%)',
  padding: '24px',
  display: 'flex',
  flexDirection: 'column',
  gap: '24px',
  fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif',
};

const headerStyles: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '16px 24px',
};

const mainStyles: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr 420px',
  gap: '24px',
  flex: 1,
};

const canvasContainerStyles: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  minHeight: '600px',
};

const sidebarStyles: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '16px',
};

const chatContainerStyles: React.CSSProperties = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
};

const messagesStyles: React.CSSProperties = {
  flex: 1,
  padding: '16px',
  display: 'flex',
  flexDirection: 'column',
  gap: '12px',
  overflowY: 'auto',
  maxHeight: '350px',
};

const chatHeaderStyles: React.CSSProperties = {
  padding: '12px 16px',
  borderBottom: '1px solid rgba(255,255,255,0.1)',
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
};

export default function App() {
  // Design state from PRS store
  const designId = usePRSStore((s) => s.designId);

  // Chat state from useChat hook (wired to real backend)
  const { messages, isStreaming, sendMessage } = useChat();

  // Add welcome message on first render if no messages
  const addMessage = useChatStore((s) => s.addMessage);
  useEffect(() => {
    if (messages.length === 0) {
      addMessage({
        id: 'welcome',
      role: 'assistant',
      content: 'Welcome to MAGNET. I\'m your AI design assistant. Describe the vessel you\'d like to design, and I\'ll guide you through the process.',
      timestamp: Date.now(),
      status: 'sent',
      });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle new design creation
  const handleNewDesign = useCallback(() => {
    // Generate a new design ID
    const newId = `MAGNET-${new Date().getFullYear()}-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;
    setDesignId(newId);
    addMessage({
      id: `design-created-${Date.now()}`,
      role: 'assistant',
      content: `New design created: **${newId}**\n\nDescribe your vessel requirements, or ask me anything about ship design.`,
      timestamp: Date.now(),
      status: 'sent',
    });
  }, [addMessage]);

  // Handle message submission
  const handleSendMessage = useCallback((content: string) => {
    if (!content.trim()) return;

    if (!designId) {
      // No design selected - prompt user
      addMessage({
        id: `no-design-${Date.now()}`,
        role: 'assistant',
        content: 'Please click **New Design** first to start a design session.',
        timestamp: Date.now(),
        status: 'sent',
      });
      return;
    }

    // Send to real backend via useChat
    sendMessage(designId, content.trim());
  }, [designId, sendMessage, addMessage]);

  return (
    <SpatialOcclusionProvider>
      <div style={appStyles}>
        {/* Header */}
        <FloatingMicroWindow
          panelId="header"
          depth="far"
          variant="default"
          enableGlass={true}
          enableGlow={false}
          style={headerStyles}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <OrbPresence state="active" size={32} />
            <div>
              <h1 style={{ fontSize: '18px', fontWeight: 600, color: '#fff', margin: 0 }}>
                MAGNET
              </h1>
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>
                Ship Design System v1.0
              </span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <PillButton variant="secondary" size="small" onClick={handleNewDesign}>
              New Design
            </PillButton>
            <PillButton variant="primary" size="small" disabled={!designId}>
              Run Analysis
            </PillButton>
          </div>
        </FloatingMicroWindow>

        {/* Main Content */}
        <div style={mainStyles}>
          {/* 3D Canvas Area */}
          <FloatingMicroWindow
            panelId="canvas"
            depth="far"
            variant="default"
            title="Hull Visualization"
            enableGlass={true}
            style={{ minHeight: '600px' }}
          >
            <div style={canvasContainerStyles}>
              <div style={{ textAlign: 'center' }}>
                <AIPresenceOrb isStreaming={isStreaming} size="lg" />
                <p style={{ color: 'rgba(255,255,255,0.6)', marginTop: '24px', fontSize: '14px' }}>
                  3D Hull Visualization
                </p>
                <p style={{ color: 'rgba(255,255,255,0.4)', fontSize: '12px', marginTop: '4px' }}>
                  Start a design to see hull geometry
                </p>
              </div>
            </div>
          </FloatingMicroWindow>

          {/* Sidebar */}
          <div style={sidebarStyles}>
            {/* Phase Progress */}
            <FloatingMicroWindow
              panelId="phases"
              depth="mid"
              variant="default"
              title="Design Progress"
              enableGlass={true}
            >
              <div style={{ padding: '16px' }}>
                <PhaseProgress
                  currentPhase="mission"
                  completedPhases={[]}
                  totalPhases={8}
                />
              </div>
            </FloatingMicroWindow>

            {/* Chat Interface */}
            <FloatingMicroWindow
              panelId="chat"
              depth="near"
              variant="default"
              enableGlass={true}
              style={chatContainerStyles}
            >
              {/* Simple chat header */}
              <div style={chatHeaderStyles}>
                <OrbPresence state={isStreaming ? 'thinking' : 'idle'} size={20} />
                <span style={{ color: '#fff', fontSize: '13px', fontWeight: 500 }}>
                  Design Assistant
                </span>
                {designId && (
                  <span style={{ color: 'rgba(255,255,255,0.4)', fontSize: '10px', marginLeft: 'auto' }}>
                    {designId}
                  </span>
                )}
                {isStreaming && (
                  <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '11px', marginLeft: designId ? '8px' : 'auto' }}>
                    thinking...
                  </span>
                )}
              </div>

              <div style={messagesStyles}>
                {messages.map((msg, index) => (
                  <ChatBubble
                    key={msg.id}
                    message={msg}
                    isLast={index === messages.length - 1}
                  />
                ))}
              </div>

              <div style={{ padding: '12px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                <ChatInput
                  onSubmit={handleSendMessage}
                  placeholder={designId ? "Ask about your design..." : "Click 'New Design' to start..."}
                  disabled={isStreaming}
                />
              </div>
            </FloatingMicroWindow>
          </div>
        </div>
      </div>
    </SpatialOcclusionProvider>
  );
}
