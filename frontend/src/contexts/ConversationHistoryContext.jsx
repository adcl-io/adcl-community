/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

/**
 * ConversationHistoryContext
 * Provides shared conversation history state across all components
 * Fixes bug where Navigation and PlaygroundPage had separate hook instances
 */
import React, { createContext, useContext } from 'react';
import { useConversationHistory } from '../hooks/useConversationHistory';

const ConversationHistoryContext = createContext(null);

export function ConversationHistoryProvider({ children }) {
  const history = useConversationHistory();

  return (
    <ConversationHistoryContext.Provider value={history}>
      {children}
    </ConversationHistoryContext.Provider>
  );
}

export function useConversationHistoryContext() {
  const context = useContext(ConversationHistoryContext);
  if (!context) {
    throw new Error('useConversationHistoryContext must be used within ConversationHistoryProvider');
  }
  return context;
}
