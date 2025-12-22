/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, Send, StopCircle, Trash2, ChevronDown, Users, User, Bot, AlertTriangle, MessageSquare, Plus, Activity } from 'lucide-react';
import { useConversationHistoryContext } from '../contexts/ConversationHistoryContext';
import UserSettings from '../components/UserSettings';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_URL = API_URL.replace('http', 'ws');

// Constants
const THINKING_PREVIEW_MAX_LENGTH = 80; // Fits mobile without wrapping
const DEFAULT_AGENT_COLOR = 'blue';

export default function PlaygroundPage() {
  // Use conversation history context
  const {
    currentSessionId,
    sessions,
    messages,
    loading: historyLoading,
    initialized,
    appendMessage,
    loadSession,
    startNewConversation,
    loadSessions,
    clearAllHistory,
    setMessages,
    setCurrentSessionId
  } = useConversationHistoryContext();

  const [input, setInput] = useState('');
  const [selectedTeam, setSelectedTeam] = useState(null);
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(false);
  const [streamingStatus, setStreamingStatus] = useState(null);
  const [showTeamSelector, setShowTeamSelector] = useState(false);
  const [executionId, setExecutionId] = useState(null);
  const [lastExecutionSummary, setLastExecutionSummary] = useState(null);
  const [sessionTokens, setSessionTokens] = useState(null); // Backend-provided data only
  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);
  const sessionIdRef = useRef(null);
  const executionStartTime = useRef(null);
  const executionCancelled = useRef(false);

  useEffect(() => {
    loadTeams();
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Start new conversation on first load if none exists
  useEffect(() => {
    if (initialized && !currentSessionId) {
      console.log('No saved session found, creating new conversation');
      // Don't create session yet - wait for first message (smart title generation)
      // startNewConversation() will be called implicitly when first message is sent
    }
  }, [initialized, currentSessionId, startNewConversation]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingStatus]);

  // Keep sessionIdRef in sync with currentSessionId from context
  useEffect(() => {
    sessionIdRef.current = currentSessionId;
  }, [currentSessionId]);

  // Fetch token data when session changes (handles mount + session switching)
  useEffect(() => {
    const fetchTokens = async () => {
      if (!currentSessionId) {
        setSessionTokens(null);
        return;
      }

      try {
        const response = await fetch(`${API_URL}/sessions/${currentSessionId}/tokens`);
        if (response.ok) {
          const tokenData = await response.json();
          setSessionTokens({
            total_input_tokens: tokenData.total_input_tokens,
            total_output_tokens: tokenData.total_output_tokens,
            total_cost: tokenData.total_cost
          });
        }
      } catch (error) {
        console.error('Failed to fetch session tokens:', error);
        setSessionTokens(null);
      }
    };

    fetchTokens();
  }, [currentSessionId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadTeams = async () => {
    try {
      const response = await axios.get(`${API_URL}/teams`);
      setTeams(response.data);
      if (response.data.length > 0 && !selectedTeam) {
        setSelectedTeam(response.data[0]);
      }
    } catch (error) {
      console.error('Failed to load teams:', error);
      setTeams([{
        id: 'default',
        name: 'Default Agent',
        description: 'General purpose AI agent',
        agents: [{ name: 'agent', role: 'assistant' }]
      }]);
      setSelectedTeam({
        id: 'default',
        name: 'Default Agent',
        description: 'General purpose AI agent',
        agents: [{ name: 'agent', role: 'assistant' }]
      });
    }
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    // ALWAYS cancel any ongoing execution before starting new one
    // Check WebSocket directly, don't rely on loading state (race conditions!)
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('🛑 Cancelling previous execution before starting new one');
      await stopExecution();
      // Give backend a moment to process cancellation
      await new Promise(resolve => setTimeout(resolve, 200));
    }

    const userMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    // Persist user message to history
    await appendMessage(userMessage);

    const messageContent = input;
    setInput('');
    setLoading(true);
    setExecutionId(null);
    executionCancelled.current = false; // Reset cancellation flag for new execution

    try {
      if (selectedTeam && selectedTeam.available_mcps) {
        await sendMessageStreaming(messageContent, userMessage);
      } else {
        await sendMessageHTTP(messageContent);
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage = {
        id: crypto.randomUUID(),
        role: 'error',
        content: `Error: ${error.message}`,
        timestamp: new Date().toISOString()
      };
      await appendMessage(errorMessage);
    } finally {
      setLoading(false);
      setStreamingStatus(null);
    }
  };

  // Helper to get a color for an agent based on their name/ID
  const getAgentColor = (agentId) => {
    if (!agentId || typeof agentId !== 'string') {
      if (import.meta.env.DEV) {
        console.warn('getAgentColor called with invalid agentId:', agentId);
      }
      return DEFAULT_AGENT_COLOR;
    }

    // Generate consistent color from agent ID using better hash
    const colors = ['blue', 'green', 'purple', 'orange', 'pink', 'cyan', 'indigo', 'teal'];
    let hash = agentId.length;
    for (let i = 0; i < agentId.length; i++) {
      hash = (hash * 31 + agentId.charCodeAt(i)) | 0;
    }
    return colors[Math.abs(hash) % colors.length];
  };

  // Agent color classes - static strings so Tailwind doesn't purge them
  const AGENT_COLORS = {
    blue: {
      avatar: 'bg-blue-500/10',
      icon: 'text-blue-500',
      bubble: 'bg-blue-500/5 border-blue-500/20 text-blue-700 dark:text-blue-300'
    },
    green: {
      avatar: 'bg-green-500/10',
      icon: 'text-green-500',
      bubble: 'bg-green-500/5 border-green-500/20 text-green-700 dark:text-green-300'
    },
    purple: {
      avatar: 'bg-purple-500/10',
      icon: 'text-purple-500',
      bubble: 'bg-purple-500/5 border-purple-500/20 text-purple-700 dark:text-purple-300'
    },
    orange: {
      avatar: 'bg-orange-500/10',
      icon: 'text-orange-500',
      bubble: 'bg-orange-500/5 border-orange-500/20 text-orange-700 dark:text-orange-300'
    },
    pink: {
      avatar: 'bg-pink-500/10',
      icon: 'text-pink-500',
      bubble: 'bg-pink-500/5 border-pink-500/20 text-pink-700 dark:text-pink-300'
    },
    cyan: {
      avatar: 'bg-cyan-500/10',
      icon: 'text-cyan-500',
      bubble: 'bg-cyan-500/5 border-cyan-500/20 text-cyan-700 dark:text-cyan-300'
    },
    indigo: {
      avatar: 'bg-indigo-500/10',
      icon: 'text-indigo-500',
      bubble: 'bg-indigo-500/5 border-indigo-500/20 text-indigo-700 dark:text-indigo-300'
    },
    teal: {
      avatar: 'bg-teal-500/10',
      icon: 'text-teal-500',
      bubble: 'bg-teal-500/5 border-teal-500/20 text-teal-700 dark:text-teal-300'
    }
  };

  // Helper to get Tailwind classes for agent color
  const getAgentColorClasses = (color = DEFAULT_AGENT_COLOR) => {
    return AGENT_COLORS[color] || AGENT_COLORS[DEFAULT_AGENT_COLOR];
  };

  // Helper to parse MCP server name from tool name
  const parseMCPServerName = (toolName) => {
    if (!toolName || typeof toolName !== 'string') return null;

    // Tool names are like "agent__code", "search_tools__search", etc.
    const parts = toolName.split('__');
    if (parts.length > 0) {
      const serverName = parts[0].replace(/_/g, ' ');
      // Capitalize first letter of each word, lowercase the rest
      return serverName
        .split(' ')
        .filter(word => word.length > 0)
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
    }
    return toolName;
  };

  // Helper to format tool call into human-readable summary (moved from backend)
  const formatToolCallSummary = (toolName, toolInput) => {
    if (!toolName || typeof toolName !== 'string') return toolName;

    // Extract base tool name (after MCP prefix)
    const parts = toolName.split('__');
    const baseTool = parts.length > 1 ? parts[1] : toolName;

    // Common file operations
    if (baseTool.toLowerCase().includes('read')) {
      const path = toolInput?.path || toolInput?.file;
      return path ? `Reading ${path}` : baseTool;
    }

    if (baseTool.toLowerCase().includes('write') || baseTool.toLowerCase().includes('create')) {
      const path = toolInput?.path || toolInput?.file;
      return path ? `Writing to ${path}` : baseTool;
    }

    if (baseTool.toLowerCase().includes('list') || baseTool.toLowerCase().includes('ls')) {
      const path = toolInput?.path;
      return path ? `Listing ${path}` : 'Listing directory';
    }

    if (baseTool.toLowerCase().includes('search') || baseTool.toLowerCase().includes('grep') || baseTool.toLowerCase().includes('find')) {
      const query = toolInput?.query || toolInput?.pattern;
      if (query) {
        const truncatedQuery = query.length > 50 ? query.substring(0, 50) + '...' : query;
        const path = toolInput?.path;
        return path ? `Searching '${truncatedQuery}' in ${path}` : `Searching for '${truncatedQuery}'`;
      }
    }

    if (baseTool.toLowerCase().includes('execute') || baseTool.toLowerCase().includes('run') || baseTool.toLowerCase().includes('command')) {
      const cmd = toolInput?.command;
      if (cmd) {
        const truncatedCmd = cmd.length > 50 ? cmd.substring(0, 50) + '...' : cmd;
        return `Executing '${truncatedCmd}'`;
      }
    }

    if (baseTool.toLowerCase().includes('scan')) {
      const target = toolInput?.host || toolInput?.target;
      return target ? `Scanning ${target}` : baseTool;
    }

    if (baseTool.toLowerCase().includes('agent')) {
      const task = toolInput?.task;
      if (task) {
        const truncatedTask = task.length > 50 ? task.substring(0, 50) + '...' : task;
        return `Running agent: '${truncatedTask}'`;
      }
    }

    // Generic fallback: show first meaningful parameter
    const keys = ['path', 'file', 'query', 'command', 'target', 'host', 'task'];
    for (const key of keys) {
      if (toolInput && toolInput[key]) {
        const value = String(toolInput[key]);
        const truncatedValue = value.length > 60 ? value.substring(0, 60) + '...' : value;
        return `${baseTool}: ${truncatedValue}`;
      }
    }

    // Last resort: tool name + param count
    const paramCount = toolInput ? Object.keys(toolInput).length : 0;
    return paramCount === 0 ? baseTool : `${baseTool} (${paramCount} params)`;
  };

  // Helper to truncate text
  const truncateText = (text, maxLength) => {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  };

  // Helper to add agent status messages to chat
  const addAgentStatusMessage = async (content, metadata = {}) => {
    const statusMessage = {
      id: crypto.randomUUID(), // Use proper UUID generation
      role: 'agent-status',
      content,
      timestamp: new Date().toISOString(),
      metadata
    };

    // Only persist important milestones, not every iteration
    if (metadata.persist === true) {
      await appendMessage(statusMessage); // This also updates setMessages
    } else {
      // For transient status messages, update streamingStatus instead of accumulating in messages
      setStreamingStatus({
        message: content,
        metadata: metadata
      });
    }
  };

  const sendMessageStreaming = (messageContent, userMessage) => {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(`${WS_URL}/ws/chat/${sessionIdRef.current}`);
      wsRef.current = ws;

      const agentActivityLog = [];
      let finalResult = null;
      let currentAgent = { id: null, role: null, color: 'blue' };

      ws.onopen = () => {
        console.log('WebSocket connected');
        ws.send(JSON.stringify({
          team_id: selectedTeam?.id || 'default',
          message: messageContent
        }));
      };

      ws.onmessage = async (event) => {
        // Check cancellation flag first to prevent processing messages after stop
        if (executionCancelled.current) {
          return;
        }

        try {
          const data = JSON.parse(event.data);

          // Check again after parsing in case cancellation happened during parse
          if (executionCancelled.current) {
            return;
          }

          console.log('WebSocket message:', data);

          if (data.type === 'execution_started') {
          setExecutionId(data.execution_id);
          executionStartTime.current = Date.now();
          await addAgentStatusMessage(
            "Starting to work on your request...",
            { type: 'execution_started', execution_id: data.execution_id, persist: true }
          );
        } else if (data.type === 'status') {
          setStreamingStatus({
            message: data.message,
            status: data.status
          });
          // Don't persist generic status messages
          await addAgentStatusMessage(data.message, { type: 'status', status: data.status });
        } else if (data.type === 'agent_start') {
          // Track current agent
          currentAgent = {
            id: data.agent_id,
            role: data.role || 'Agent',
            color: getAgentColor(data.agent_id)
          };

          agentActivityLog.push({
            type: 'start',
            agent_id: data.agent_id,
            role: data.role,
            message: data.message,
            progress: data.progress
          });
          setStreamingStatus({
            message: data.message,
            agent: data.role,
            progress: data.progress
          });

          // Conversational message - persist agent start
          await addAgentStatusMessage(
            `${currentAgent.role} is starting to work on your request...`,
            {
              type: 'agent_start',
              agent_id: data.agent_id,
              agent_role: currentAgent.role,
              agent_color: currentAgent.color,
              progress: data.progress,
              persist: true
            }
          );
        } else if (data.type === 'agent_iteration') {
          // Update session tokens from backend (backend is source of truth)
          if (data.cumulative_tokens) {
            setSessionTokens(data.cumulative_tokens);
          }

          // Build detailed iteration data for metadata
          const iterationData = {
            type: 'agent_iteration',
            iteration: data.iteration,
            max_iterations: data.max_iterations,
            token_usage: data.token_usage,
            model: data.model,
            tools_used: data.tools_used,
            stop_reason: data.stop_reason,
            thinking_preview: data.thinking_preview,
            agent_id: currentAgent.id,
            agent_role: currentAgent.role,
            agent_color: currentAgent.color
          };

          // Build user-friendly message with agent name and MCP context
          let statusContent = '';
          const agentName = currentAgent?.role || data.role || 'Agent';

          // Show tool summaries if available (more informative than just MCP names)
          if (data.tools_used && Array.isArray(data.tools_used) && data.tools_used.length > 0) {
            const toolDescriptions = data.tools_used
              .filter(t => t && (t.summary || t.name))
              .map(t => t.summary || t.name)
              .join(', ');

            if (toolDescriptions) {
              statusContent = `${agentName} is using tools:\n🔧 ${toolDescriptions}`;
            } else {
              statusContent = `${agentName} is working...`;
            }
          } else {
            // No tools, just thinking
            if (data.iteration === 1) {
              statusContent = `${agentName} is thinking...`;
            } else {
              statusContent = `${agentName} is analyzing...`;
            }
          }

          // Don't include thinking in status content - will be shown separately in collapsible

          // Persist iterations with tool usage or thinking (valuable context)
          const shouldPersist = (data.tools_used && data.tools_used.length > 0) || data.thinking;
          await addAgentStatusMessage(statusContent, {
            ...iterationData,
            thinking: data.thinking,  // Store thinking in metadata, not content
            thinking_preview: data.thinking_preview,
            persist: shouldPersist
          });
        } else if (data.type === 'iteration_start') {
          // NEW: Mark when each iteration starts
          const agentName = currentAgent?.role || 'Agent';
          await addAgentStatusMessage(
            `${agentName} - Iteration ${data.iteration}/${data.max_iterations}`,
            {
              type: 'iteration_start',
              iteration: data.iteration,
              max_iterations: data.max_iterations,
              agent_id: currentAgent.id,
              agent_role: currentAgent.role,
              agent_color: currentAgent.color,
              persist: false  // Don't persist - visual progress indicator
            }
          );
        } else if (data.type === 'agent_reasoning') {
          // NEW: Show agent's thinking inline (ChatGPT-style)
          const agentName = currentAgent?.role || 'Agent';
          const reasoningPreview = truncateText(data.reasoning, 300);
          await addAgentStatusMessage(
            `💭 ${reasoningPreview}`,
            {
              type: 'agent_reasoning',
              reasoning: data.reasoning,
              reasoning_preview: reasoningPreview,
              iteration: data.iteration,
              agent_id: currentAgent.id,
              agent_role: currentAgent.role,
              agent_color: currentAgent.color,
              persist: true  // Persist reasoning - it's valuable
            }
          );
        } else if (data.type === 'tool_execution') {
          // Real-time update for individual tool calls - show inline
          const agentName = currentAgent?.role || 'Agent';
          const toolSummary = formatToolCallSummary(data.tool_name, data.tool_input);
          const toolMessage = `🔧 ${toolSummary}...`;
          await addAgentStatusMessage(toolMessage, {
            type: 'tool_execution',
            tool_name: data.tool_name,
            tool_summary: toolSummary,
            iteration: data.iteration,
            agent_id: currentAgent.id,
            agent_role: currentAgent.role,
            agent_color: currentAgent.color,
            persist: false  // Don't persist - we'll show the result instead
          });
        } else if (data.type === 'tool_result') {
          // NEW: Show tool results inline (ChatGPT-style)
          const successIcon = data.success ? '✅' : '❌';
          const toolSummary = formatToolCallSummary(data.tool_name, data.tool_input);
          const resultPreview = truncateText(JSON.stringify(data.result), 1000);
          const resultMessage = data.success
            ? `${successIcon} ${toolSummary}: completed`
            : `${successIcon} ${toolSummary}: ${data.result?.error || 'failed'}`;

          await addAgentStatusMessage(resultMessage, {
            type: 'tool_result',
            tool_name: data.tool_name,
            tool_summary: toolSummary,
            result: data.result,
            result_preview: resultPreview,
            success: data.success,
            iteration: data.iteration,
            agent_id: currentAgent.id,
            agent_role: currentAgent.role,
            agent_color: currentAgent.color,
            persist: true  // Persist tool results - they're important
          });
        } else if (data.type === 'agent_answer') {
          // NEW: Show agent's final answer before completion
          const agentName = currentAgent?.role || 'Agent';
          const answerPreview = truncateText(data.answer, 500);
          await addAgentStatusMessage(
            answerPreview,
            {
              type: 'agent_answer',
              answer: data.answer,
              answer_preview: answerPreview,
              iteration: data.iteration,
              total_iterations: data.total_iterations,
              status: data.status,
              agent_id: currentAgent.id,
              agent_role: currentAgent.role,
              agent_color: currentAgent.color,
              persist: true  // Persist final answer
            }
          );
        } else if (data.type === 'agent_complete') {
          agentActivityLog.push({
            type: 'complete',
            agent_id: data.agent_id,
            role: data.role,
            message: data.message,
            answer_preview: data.answer_preview,
            tools_used: data.tools_used,
            progress: data.progress
          });
          setStreamingStatus({
            message: data.message,
            agent: data.role,
            progress: data.progress
          });

          // Conversational completion message - persist this milestone
          const agentName = data.role || 'Agent';
          let completionMsg = `${agentName} has finished`;
          // Use full answer if available, otherwise use preview
          if (data.answer) {
            completionMsg += ': ' + data.answer;
          } else if (data.answer_preview) {
            completionMsg += ': ' + data.answer_preview;
          } else {
            completionMsg += ' their work.';
          }

          await addAgentStatusMessage(
            completionMsg,
            { type: 'agent_complete', agent_id: data.agent_id, role: data.role, status: data.status, answer: data.answer, persist: true }
          );
        } else if (data.type === 'complete') {
          finalResult = data.result;

          // Defensive check: look for errors in agent results
          const agentErrors = [];
          if (data.result?.agent_results) {
            data.result.agent_results.forEach(ar => {
              if (ar.status === 'error') {
                agentErrors.push(`${ar.role || ar.agent_id}: ${ar.error || 'Unknown error'}`);
              }
            });
          }

          // If errors found, treat as error instead of success
          if (agentErrors.length > 0) {
            const errorMessage = {
              id: crypto.randomUUID(),
              role: 'error',
              content: `Team execution failed:\n\n${agentErrors.join('\n')}`,
              timestamp: new Date().toISOString()
            };
            await appendMessage(errorMessage);
            ws.close();
            reject(new Error(agentErrors.join('; ')));
            return;
          }

          // Calculate execution summary
          const executionTime = executionStartTime.current
            ? ((Date.now() - executionStartTime.current) / 1000).toFixed(1)
            : null;

          // Count unique agents
          const uniqueAgents = new Set(agentActivityLog.map(a => a.agent_id).filter(Boolean));
          const agentCount = uniqueAgents.size || selectedTeam?.agents?.length || 0;

          // Fetch final token counts from backend (single source of truth)
          try {
            const tokenResponse = await fetch(`${API_URL}/sessions/${sessionIdRef.current}/tokens`);
            if (tokenResponse.ok) {
              const tokenData = await tokenResponse.json();
              setSessionTokens({
                total_input_tokens: tokenData.total_input_tokens,
                total_output_tokens: tokenData.total_output_tokens,
                total_cost: tokenData.total_cost
              });
            }
          } catch (error) {
            console.error('Failed to fetch session tokens:', error);
          }

          // Set execution summary for display (no token info here, shown in header)
          setLastExecutionSummary({
            agentCount,
            iterations: data.result?.total_iterations || 0,
            time: executionTime
          });

          const assistantMessage = {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: data.result.answer || 'Task completed.',
            agent: selectedTeam?.name || 'Agent',
            timestamp: new Date().toISOString(),
            agentActivity: agentActivityLog,
            team_result: data.result,
            metadata: {
              agentActivity: agentActivityLog,
              team_result: data.result
            }
          };

          // Persist assistant message to history
          await appendMessage(assistantMessage);

          ws.close();
          resolve();
        } else if (data.type === 'error') {
          const errorMessage = {
            id: crypto.randomUUID(),
            role: 'error',
            content: `Error: ${data.error}`,
            timestamp: new Date().toISOString()
          };
          await appendMessage(errorMessage);
          ws.close();
          reject(new Error(data.error));
        }
        } catch (err) {
          console.error('WebSocket handler error:', err);
          const errorMessage = {
            id: crypto.randomUUID(),
            role: 'error',
            content: `Internal error: ${err.message}`,
            timestamp: new Date().toISOString()
          };
          setMessages(prev => [...prev, errorMessage]);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };

      ws.onclose = () => {
        console.log('WebSocket closed');
        // Only null the ref if it's still pointing to this WebSocket instance
        if (wsRef.current === ws) {
          wsRef.current = null;
        }
      };
    });
  };

  const sendMessageHTTP = async (messageContent) => {
    const conversationHistory = messages
      .filter(m => m.role !== 'error' && m.role !== 'agent-status')
      .map(m => ({
        role: m.role,
        content: m.content
      }));

    const response = await axios.post(`${API_URL}/chat`, {
      team_id: selectedTeam?.id || 'default',
      message: messageContent,
      history: conversationHistory
    });

    const assistantMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: response.data.response,
      agent: response.data.agent || 'Agent',
      timestamp: new Date().toISOString(),
      reasoning: response.data.reasoning,
      team_responses: response.data.team_responses
    };

    // Persist assistant message to history
    await appendMessage(assistantMessage);
  };

  const stopExecution = async () => {
    // Set cancellation flag to prevent race conditions with in-flight messages
    executionCancelled.current = true;

    // Notify backend before closing connection
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({
          type: 'cancel_execution',
          execution_id: executionId
        }));
      } catch (error) {
        console.error('Failed to send cancellation to backend:', error);
      }
    }

    // Close WebSocket connection if active
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // Reset loading state
    setLoading(false);
    setStreamingStatus(null);

    // Add cancellation message to chat
    const cancelMessage = {
      id: crypto.randomUUID(),
      role: 'agent-status',
      content: 'Execution cancelled by user.',
      timestamp: new Date().toISOString(),
      metadata: { type: 'cancelled' }
    };
    await appendMessage(cancelMessage);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleNewConversation = async () => {
    // Don't create session yet - wait for first message to use as title
    setMessages([]);
    setCurrentSessionId(null);
    setSessionTokens(null);
    await loadSessions();
  };

  const handleLoadConversation = async (sessionId) => {
    await loadSession(sessionId);
    // Token count will be fetched automatically by useEffect when currentSessionId changes
  };

  const handleClearHistory = () => {
    clearAllHistory();
    // Don't create session yet - wait for first message
    setMessages([]);
    setCurrentSessionId(null);
    setSessionTokens(null);
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-border bg-card flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-foreground">
              {selectedTeam?.name || 'ADCL Chat'}
            </h2>
            <Button
              size="sm"
              variant="outline"
              onClick={handleNewConversation}
            >
              <Plus className="h-4 w-4 mr-2" />
              New Chat
            </Button>
          </div>

          {/* Token Usage & Cost - Backend provided */}
          <div className="flex items-center gap-4 text-xs font-mono text-muted-foreground">
            {sessionTokens && (sessionTokens.total_input_tokens + sessionTokens.total_output_tokens > 0) && (
              <>
                <div className="flex items-center gap-2 px-3 py-1 rounded-md bg-muted/50">
                  <span className="font-semibold text-foreground">Tokens:</span>
                  <span className="text-blue-600 dark:text-blue-400">
                    {sessionTokens.total_input_tokens.toLocaleString()} in
                  </span>
                  <span className="opacity-30">/</span>
                  <span className="text-green-600 dark:text-green-400">
                    {sessionTokens.total_output_tokens.toLocaleString()} out
                  </span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1 rounded-md bg-muted/50">
                  <span className="font-semibold text-foreground">Cost:</span>
                  <span className="text-orange-600 dark:text-orange-400">
                    ${sessionTokens.total_cost.toFixed(4)}
                  </span>
                </div>
              </>
            )}
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowTeamSelector(true)}
              className="gap-2"
            >
              <Users className="h-4 w-4" />
              <span className="font-medium">{selectedTeam?.name || 'Select Team'}</span>
              {selectedTeam?.agents && selectedTeam.agents.length > 0 && (
                <span className="text-xs opacity-60 font-mono">
                  ({selectedTeam.agents.length} {selectedTeam.agents.length === 1 ? 'agent' : 'agents'})
                </span>
              )}
            </Button>
            <UserSettings onClearHistory={handleClearHistory} />
          </div>
        </div>

        {/* Messages Area - Clean like ChatGPT */}
        <ScrollArea className="flex-1 p-6">
          <div className="max-w-3xl mx-auto space-y-4">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center py-12">
                <MessageSquare className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold text-foreground mb-2">Start a conversation</h3>
                <p className="text-sm text-muted-foreground">
                  Ask questions or request assistance
                </p>
              </div>
            )}

            {messages.map((message) => {
              const agentColor = message.role === 'agent-status' && message.metadata?.agent_color
                ? getAgentColorClasses(message.metadata.agent_color)
                : getAgentColorClasses('blue');

              // Make intermediate status messages more compact
              // Explicit null check on metadata to handle legacy messages from history
              const isIntermediateStatus = message.role === 'agent-status' &&
                message.metadata &&
                message.metadata.persist !== true &&
                (message.metadata.type === 'agent_iteration' ||
                 message.metadata.type === 'tool_execution' ||
                 message.metadata.type === 'iteration_start');

              // Special styling for reasoning (thinking) messages
              const isThinkingMessage = message.role === 'agent-status' &&
                message.metadata?.type === 'agent_reasoning';

              // Special styling for tool results
              const isToolResult = message.role === 'agent-status' &&
                message.metadata?.type === 'tool_result';

              // Special styling for final answers
              const isFinalAnswer = message.role === 'agent-status' &&
                message.metadata?.type === 'agent_answer';

              return (
              <div key={message.id} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'} ${isIntermediateStatus ? 'opacity-70' : ''}`}>
                {message.role !== 'user' && (
                  <div className="flex-shrink-0">
                    <div className={`h-8 w-8 rounded-full flex items-center justify-center ${
                      message.role === 'agent-status'
                        ? agentColor.avatar
                        : 'bg-primary/10'
                    }`}>
                      {message.role === 'agent-status' ? (
                        <Activity className={`h-4 w-4 ${agentColor.icon}`} />
                      ) : (
                        <Bot className="h-5 w-5 text-primary" />
                      )}
                    </div>
                    {message.role === 'agent-status' && message.metadata?.agent_role?.trim() && (
                      <div className="text-xs font-medium mt-1 text-center text-muted-foreground">
                        {message.metadata.agent_role}
                      </div>
                    )}
                  </div>
                )}

                <div className={`flex-1 max-w-2xl ${message.role === 'user' ? 'flex justify-end' : ''}`}>
                  <div
                    className={`${
                      isIntermediateStatus
                        ? 'rounded-lg px-3 py-1.5'
                        : isThinkingMessage
                        ? 'rounded-xl px-4 py-2.5 border-l-4'
                        : isFinalAnswer
                        ? 'rounded-xl px-4 py-3 ring-2 ring-offset-2'
                        : 'rounded-2xl px-4 py-3'
                    } border ${
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : message.role === 'error'
                        ? 'bg-destructive/10 border-destructive text-destructive'
                        : isThinkingMessage
                        ? 'bg-muted/30 border-muted border-l-blue-500 dark:border-l-blue-400'
                        : isFinalAnswer
                        ? 'bg-green-500/5 border-green-500/30 ring-green-500/20 text-green-700 dark:text-green-300'
                        : isToolResult
                        ? message.metadata?.success
                          ? 'bg-green-500/5 border-green-500/20 text-green-700 dark:text-green-300'
                          : 'bg-red-500/5 border-red-500/20 text-red-700 dark:text-red-300'
                        : message.role === 'agent-status'
                        ? agentColor.bubble
                        : 'bg-muted border-transparent'
                    }`}
                  >
                    <div className={`whitespace-pre-wrap ${
                      isIntermediateStatus ? 'text-xs' : isThinkingMessage ? 'text-sm italic' : 'text-sm'
                    }`}>{message.content}</div>

                    {/* Only show details for important messages, not intermediate status */}
                    {!isIntermediateStatus && (
                      <>
                        {/* Full reasoning for thinking messages - collapsed by default */}
                        {isThinkingMessage && message.metadata?.reasoning && (
                          <Collapsible className="mt-2">
                            <CollapsibleTrigger className="flex items-center gap-2 text-xs text-muted-foreground/70 hover:text-muted-foreground pt-2 border-t border-current/10 w-full">
                              <ChevronDown className="h-3 w-3" />
                              <span>View full reasoning</span>
                            </CollapsibleTrigger>
                            <CollapsibleContent>
                              <div className="mt-2 text-xs text-muted-foreground/80 whitespace-pre-wrap font-mono">
                                {message.metadata.reasoning}
                              </div>
                            </CollapsibleContent>
                          </Collapsible>
                        )}

                        {/* Full answer for final answer messages - collapsed by default */}
                        {isFinalAnswer && message.metadata?.answer && message.metadata.answer !== message.content && (
                          <Collapsible className="mt-2">
                            <CollapsibleTrigger className="flex items-center gap-2 text-xs text-muted-foreground/70 hover:text-muted-foreground pt-2 border-t border-current/10 w-full">
                              <ChevronDown className="h-3 w-3" />
                              <span>View full answer</span>
                            </CollapsibleTrigger>
                            <CollapsibleContent>
                              <div className="mt-2 text-sm whitespace-pre-wrap">
                                {message.metadata.answer}
                              </div>
                            </CollapsibleContent>
                          </Collapsible>
                        )}

                        {/* Tool result details - collapsed by default */}
                        {isToolResult && message.metadata?.result_preview && (
                          <Collapsible className="mt-2">
                            <CollapsibleTrigger className="flex items-center gap-2 text-xs text-muted-foreground/70 hover:text-muted-foreground pt-2 border-t border-current/10 w-full">
                              <ChevronDown className="h-3 w-3" />
                              <span>View tool output</span>
                            </CollapsibleTrigger>
                            <CollapsibleContent>
                              <div className="mt-2 text-xs text-muted-foreground/80 whitespace-pre-wrap font-mono">
                                {message.metadata.result_preview}
                              </div>
                            </CollapsibleContent>
                          </Collapsible>
                        )}

                        {/* Legacy thinking content - collapsed by default */}
                        {!isThinkingMessage && message.role === 'agent-status' && message.metadata?.thinking && (
                          <Collapsible className="mt-2">
                            <CollapsibleTrigger className="flex items-center gap-2 text-xs text-muted-foreground/70 hover:text-muted-foreground pt-2 border-t border-current/10 w-full">
                              <ChevronDown className="h-3 w-3" />
                              <span>💭 View reasoning</span>
                            </CollapsibleTrigger>
                            <CollapsibleContent>
                              <div className="mt-2 text-xs text-muted-foreground/80 whitespace-pre-wrap font-mono">
                                {message.metadata.thinking}
                              </div>
                            </CollapsibleContent>
                          </Collapsible>
                        )}

                        {/* Inline technical metrics - collapsed by default for cleaner UI */}
                        {message.role === 'agent-status' && message.metadata && (message.metadata.model || message.metadata.token_usage || message.metadata.tools_used) && (
                          <Collapsible className="mt-2">
                            <CollapsibleTrigger className="flex items-center gap-2 text-xs text-muted-foreground/70 hover:text-muted-foreground pt-2 border-t border-current/10 w-full">
                              <ChevronDown className="h-3 w-3" />
                              <span>Technical details</span>
                            </CollapsibleTrigger>
                            <CollapsibleContent>
                              <div className="mt-2">
                                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-mono text-muted-foreground/70">
                                  {message.metadata?.model && (
                                    <span>Model: {message.metadata.model}</span>
                                  )}
                                  {message.metadata?.token_usage && (
                                    <span>
                                      Tokens: {message.metadata.token_usage.input_tokens?.toLocaleString() || 0} in / {message.metadata.token_usage.output_tokens?.toLocaleString() || 0} out
                                    </span>
                                  )}
                                  {message.metadata?.execution_time && (
                                    <span>Time: {message.metadata.execution_time}s</span>
                                  )}
                                  {message.metadata?.iteration && (
                                    <span>{message.metadata.iteration}/{message.metadata.max_iterations} iterations</span>
                                  )}
                                  {message.metadata?.tools_used && Array.isArray(message.metadata.tools_used) && message.metadata.tools_used.length > 0 && (
                                    <span className="flex items-center gap-1">
                                      <span className="opacity-50">|</span>
                                      MCP: {[...new Set(
                                        message.metadata.tools_used
                                          .filter(t => t && t.name)
                                          .map(t => parseMCPServerName(t.name))
                                          .filter(Boolean)
                                      )].join(', ')}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </CollapsibleContent>
                          </Collapsible>
                        )}
                      </>
                    )}

                    {message.agentActivity && message.agentActivity.length > 0 && (
                      <Collapsible className="mt-3">
                        <CollapsibleTrigger className="flex items-center gap-2 text-xs opacity-70 hover:opacity-100">
                          <ChevronDown className="h-3 w-3" />
                          View details ({message.agentActivity.length} steps)
                        </CollapsibleTrigger>
                        <CollapsibleContent className="mt-2 space-y-2">
                          {message.agentActivity.map((activity, idx) => (
                            <div key={idx} className="text-xs opacity-70 border-l-2 border-primary/30 pl-3 py-1">
                              <div className="font-medium">{activity.role}</div>
                              <div>{activity.message}</div>
                            </div>
                          ))}
                        </CollapsibleContent>
                      </Collapsible>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1 px-1">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>

                {message.role === 'user' && (
                  <div className="flex-shrink-0">
                    <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center">
                      <User className="h-5 w-5" />
                    </div>
                  </div>
                )}
              </div>
              );
            })}

            {streamingStatus && (
              <div className="flex gap-3 justify-start">
                <div className="flex-shrink-0">
                  <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Bot className="h-5 w-5 text-primary" />
                  </div>
                </div>
                <div className="flex-1 max-w-2xl">
                  <div className="rounded-2xl px-4 py-3 bg-muted">
                    <div className="flex items-center gap-2 text-sm">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span className="text-muted-foreground">{streamingStatus.message}</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>

        {/* Execution Summary Bar - Developer metrics */}
        {lastExecutionSummary && (
          <div className="border-t border-border bg-muted/30 px-4 py-2">
            <div className="max-w-3xl mx-auto flex items-center justify-between text-xs font-mono text-muted-foreground">
              <div className="flex items-center gap-4">
                <span className="font-semibold text-foreground">Last run:</span>
                {lastExecutionSummary.agentCount > 0 && (
                  <span>{lastExecutionSummary.agentCount} {lastExecutionSummary.agentCount === 1 ? 'agent' : 'agents'}</span>
                )}
                {lastExecutionSummary.iterations > 0 && (
                  <span>{lastExecutionSummary.iterations} {lastExecutionSummary.iterations === 1 ? 'iteration' : 'iterations'}</span>
                )}
                {lastExecutionSummary.time && (
                  <span>{lastExecutionSummary.time}s</span>
                )}
              </div>
              <button
                onClick={() => setLastExecutionSummary(null)}
                className="text-muted-foreground/50 hover:text-muted-foreground"
                title="Dismiss"
              >
                ✕
              </button>
            </div>
          </div>
        )}

        {/* Input Area - Clean like ChatGPT */}
        <div className="border-t border-border bg-card p-4">
          <div className="max-w-3xl mx-auto">
            <div className="flex gap-2">
              <Textarea
                id="chat-message-input"
                name="message"
                placeholder={
                  selectedTeam?.name
                    ? `Ask ${selectedTeam.name}...`
                    : "Select a team to get started..."
                }
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={false}  // Allow typing during execution so users can cancel by sending new message
                rows={1}
                className="resize-none min-h-[44px] max-h-32"
              />
              <Button
                onClick={loading ? stopExecution : sendMessage}
                disabled={!loading && !input.trim()}
                size="lg"
                className="h-[44px]"
                variant={loading ? "destructive" : "default"}
                aria-label={loading ? "Stop execution" : "Send message"}
              >
                {loading ? (
                  <StopCircle className="h-5 w-5" />
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Team Selector Modal/Dropdown */}
      {showTeamSelector && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowTeamSelector(false)}>
          <Card className="w-96 max-h-[80vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <CardHeader>
              <CardTitle>Select Team</CardTitle>
              <CardDescription>Choose an agent team for your conversation</CardDescription>
            </CardHeader>
            <CardContent className="p-4 space-y-2 max-h-96 overflow-y-auto">
              {teams.map(team => (
                <div
                  key={team.id}
                  className={`cursor-pointer rounded-lg p-3 border transition-all ${
                    selectedTeam?.id === team.id
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50'
                  }`}
                  onClick={() => {
                    setSelectedTeam(team);
                    setShowTeamSelector(false);
                  }}
                >
                  <div className="font-medium">{team.name}</div>
                  <div className="text-sm text-muted-foreground">{team.description}</div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
