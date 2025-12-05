/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

/**
 * useConversationHistory Hook
 * Manages conversation history with persistence via History MCP Server
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const HISTORY_MCP_URL = import.meta.env.VITE_HISTORY_MCP_URL || 'http://localhost:7004';

/**
 * Sanitize title: remove newlines/tabs, trim whitespace, truncate with ellipsis
 */
function sanitizeTitle(text, maxLength = 60) {
  if (!text || typeof text !== 'string') return null;

  // Remove newlines, tabs, and normalize whitespace
  const cleaned = text.replace(/[\n\r\t]+/g, ' ').trim();

  if (cleaned.length === 0) return null;
  if (cleaned.length <= maxLength) return cleaned;

  // Truncate and add ellipsis
  return cleaned.substring(0, maxLength) + '...';
}

export function useConversationHistory() {
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [initialized, setInitialized] = useState(false);

  // Prevent race condition: track if session creation is in progress
  const sessionCreationInProgress = useRef(false);
  // Track current session ID immediately (before state update propagates)
  const currentSessionIdRef = useRef(null);

  // Load recent sessions on mount
  useEffect(() => {
    const init = async () => {
      await loadSessions();
      // Don't auto-load last session - start fresh or wait for user action
      setInitialized(true);
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Only run once on mount

  /**
   * Load list of conversation sessions
   */
  const loadSessions = useCallback(async () => {
    try {
      console.log('[History] Loading sessions...');
      const response = await axios.post(`${HISTORY_MCP_URL}/mcp/call_tool`, {
        tool: 'list_sessions',
        arguments: {
          limit: 50,
          status: 'active'
        }
      });

      const result = JSON.parse(response.data.content[0].text);
      if (result.success) {
        console.log('[History] Loaded sessions:', result.sessions.length);
        setSessions(result.sessions || []);
      }
    } catch (err) {
      console.warn('[History] Failed to load sessions:', err.message);
      // Silently fail - history might not be installed yet
    }
  }, []);

  /**
   * Create a new conversation session
   */
  const createSession = useCallback(async (title = null, metadata = {}) => {
    // Prevent race condition: don't create multiple sessions simultaneously
    if (sessionCreationInProgress.current) {
      console.warn('[History] Session creation already in progress, skipping');
      return null;
    }

    sessionCreationInProgress.current = true;
    setLoading(true);
    setError(null);

    try {
      console.log('[History] Creating new session:', title);
      const response = await axios.post(`${HISTORY_MCP_URL}/mcp/call_tool`, {
        tool: 'create_session',
        arguments: {
          title: title, // No fallback - let backend handle defaults
          metadata
        }
      });

      const result = JSON.parse(response.data.content[0].text);

      if (result.success) {
        const sessionId = result.session_id;
        console.log('[History] Created session:', sessionId);
        // Update ref immediately (before state propagates)
        currentSessionIdRef.current = sessionId;
        setCurrentSessionId(sessionId);
        setMessages([]);
        await loadSessions(); // Refresh session list
        return sessionId;
      } else {
        throw new Error(result.error || 'Failed to create session');
      }
    } catch (err) {
      console.error('[History] Failed to create session:', err);
      setError(err.message);
      // No fallback - fail gracefully and show error
      // Session will be null, user can continue but history won't be saved
      return null;
    } finally {
      sessionCreationInProgress.current = false;
      setLoading(false);
    }
  }, [loadSessions]);

  /**
   * Load an existing conversation session
   */
  const loadSession = useCallback(async (sessionId) => {
    setLoading(true);
    setError(null);

    try {
      console.log('[History] Loading session:', sessionId);
      const response = await axios.post(`${HISTORY_MCP_URL}/mcp/call_tool`, {
        tool: 'get_messages',
        arguments: {
          session_id: sessionId,
          limit: 100,
          reverse: false // Get oldest first for chronological display
        }
      });

      const result = JSON.parse(response.data.content[0].text);

      if (result.success) {
        // Convert history format to UI format
        const loadedMessages = (result.messages || []).map(msg => ({
          id: msg.id,
          role: msg.type,
          content: msg.content,
          timestamp: msg.timestamp,
          metadata: msg.metadata || {},
          agent: msg.agent,
          tools: msg.tools
        }));

        console.log('[History] Loaded messages:', loadedMessages.length);
        setMessages(loadedMessages);
        // Update ref immediately
        currentSessionIdRef.current = sessionId;
        setCurrentSessionId(sessionId);
      } else {
        throw new Error(result.error || 'Failed to load session');
      }
    } catch (err) {
      console.error('[History] Failed to load session:', err);
      setError(err.message);
      // No localStorage fallback - fail gracefully
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Append a message to the current session
   */
  const appendMessage = useCallback(async (message) => {
    // Ensure we have a session
    // Use ref for immediate access (before state propagates)
    let sessionId = currentSessionIdRef.current || currentSessionId;
    if (!sessionId && !sessionCreationInProgress.current) {
      console.log('[History] No session, creating one...');
      // Use first user message as title (smart title generation with sanitization)
      const smartTitle = (message.role === 'user' && message.content)
        ? sanitizeTitle(message.content)
        : null;
      sessionId = await createSession(smartTitle);
    }

    // Add to UI immediately for responsiveness
    const uiMessage = {
      id: message.id || `msg-${Date.now()}`,
      role: message.role || message.type,
      content: message.content,
      timestamp: message.timestamp || new Date().toISOString(),
      metadata: message.metadata || {},
      agent: message.agent,
      tools: message.tools
    };

    setMessages(prev => [...prev, uiMessage]);

    // Persist to history MCP in background
    try {
      console.log('[History] Persisting message to session:', sessionId);
      const response = await axios.post(`${HISTORY_MCP_URL}/mcp/call_tool`, {
        tool: 'append_message',
        arguments: {
          session_id: sessionId,
          message_type: message.role || message.type,
          content: message.content,
          metadata: {
            agent: message.agent,
            tools: message.tools,
            ...message.metadata
          }
        }
      });

      const result = JSON.parse(response.data.content[0].text);
      if (result.success) {
        console.log('[History] Message persisted:', result.message_id);
      }

      // Refresh sessions list to update preview
      loadSessions();
    } catch (err) {
      console.error('[History] Failed to persist message:', err);
      // No localStorage fallback - message is already in UI state
      // History won't be persisted but user can continue using the app
    }

    return uiMessage;
  }, [currentSessionId, messages, createSession, loadSessions]);

  /**
   * Start a new conversation (create new session, clear current messages)
   */
  const startNewConversation = useCallback(async (title = null) => {
    const sessionId = await createSession(title);
    setMessages([]);
    return sessionId;
  }, [createSession]);

  /**
   * Clear current conversation (keep session, just clear UI)
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  /**
   * Search conversation titles
   */
  const searchConversations = useCallback(async (query) => {
    try {
      const response = await axios.post(`${HISTORY_MCP_URL}/mcp/call_tool`, {
        tool: 'search_titles',
        arguments: {
          query,
          limit: 50
        }
      });

      const result = JSON.parse(response.data.content[0].text);
      return result.success ? result.results : [];
    } catch (err) {
      console.error('Search failed:', err);
      return [];
    }
  }, []);

  /**
   * Search message content across all conversations
   */
  const searchMessages = useCallback(async (query) => {
    try {
      const response = await axios.post(`${HISTORY_MCP_URL}/mcp/call_tool`, {
        tool: 'search_messages',
        arguments: {
          query,
          limit: 100
        }
      });

      const result = JSON.parse(response.data.content[0].text);
      return result.success ? result.results : [];
    } catch (err) {
      console.error('[History] Message search failed:', err);
      return [];
    }
  }, []);

  /**
   * Clear all history (local state only - MCP server files remain)
   */
  const clearAllHistory = useCallback(() => {
    setSessions([]);
    setMessages([]);
    currentSessionIdRef.current = null;
    setCurrentSessionId(null);
  }, []);

  return {
    // State
    currentSessionId,
    sessions,
    messages,
    loading,
    error,
    initialized,

    // Actions
    createSession,
    loadSession,
    appendMessage,
    startNewConversation,
    clearMessages,
    clearAllHistory,
    loadSessions,
    searchConversations,
    searchMessages,

    // Setters for direct manipulation if needed
    setMessages,
    setCurrentSessionId
  };
}
