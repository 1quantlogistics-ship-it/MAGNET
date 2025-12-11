/**
 * MAGNET App - Main Application Component
 *
 * Composes the VisionOS-style UI components into the main ship design interface.
 */

import React, { useState } from 'react';
import { FloatingMicroWindow } from './components/core/FloatingMicroWindow';
import { OrbPresence } from './components/core/OrbPresence';
import { PillButton } from './components/core/PillButton';
import { AIPresenceOrb } from './components/chat/AIPresenceOrb';
import { ChatBubble } from './components/chat/ChatBubble';
import { ChatInput } from './components/chat/ChatInput';
import { PhaseProgress } from './components/prs/PhaseProgress';
import { SpatialOcclusionProvider } from './contexts/SpatialOcclusionContext';
import type { ChatMessage } from './types/chat';

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
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Welcome to MAGNET. I\'m your AI design assistant. Describe the vessel you\'d like to design, and I\'ll guide you through the process.',
      timestamp: Date.now(),
      status: 'sent',
    },
  ]);
  const [isTyping, setIsTyping] = useState(false);

  const handleSendMessage = (content: string) => {
    if (!content.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: content.trim(),
      timestamp: Date.now(),
      status: 'sent',
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsTyping(true);

    // Simulate AI response
    setTimeout(() => {
      setIsTyping(false);
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'I understand your requirements. Let me analyze the mission profile and propose an initial hull form...',
        timestamp: Date.now(),
        status: 'sent',
      };
      setMessages((prev) => [...prev, assistantMessage]);
    }, 1500);
  };

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
            <PillButton variant="secondary" size="small">
              New Design
            </PillButton>
            <PillButton variant="primary" size="small">
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
                <AIPresenceOrb isStreaming={isTyping} size="lg" />
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
                <OrbPresence state={isTyping ? 'thinking' : 'idle'} size={20} />
                <span style={{ color: '#fff', fontSize: '13px', fontWeight: 500 }}>
                  Design Assistant
                </span>
                {isTyping && (
                  <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '11px', marginLeft: 'auto' }}>
                    typing...
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
                  placeholder="Describe your vessel requirements..."
                  disabled={isTyping}
                />
              </div>
            </FloatingMicroWindow>
          </div>
        </div>
      </div>
    </SpatialOcclusionProvider>
  );
}
