/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import WebSocketService from '../services/WebSocketService';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Custom hook for workflow execution
 * Uses WebSocketService for communication
 * Manages execution state only
 */
function useExecution() {
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState(null);
  const wsServiceRef = useRef(null);
  const logsRef = useRef([]);

  // Initialize WebSocket service
  if (!wsServiceRef.current) {
    wsServiceRef.current = new WebSocketService(API_URL);
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsServiceRef.current) {
        wsServiceRef.current.close();
      }
    };
  }, []);

  const executeWorkflow = useCallback((nodes, edges, onNodeStateUpdate) => {
    setExecuting(true);
    setResult(null);
    logsRef.current = [];

    const sessionId = `session-${Date.now()}`;
    const wsService = wsServiceRef.current;

    // Handle messages
    const unsubscribeMessage = wsService.on('message', (message) => {
      handleMessage(message, onNodeStateUpdate);
    });

    // Handle errors
    const unsubscribeError = wsService.on('error', (error) => {
      console.error('WebSocket error:', error);
      setResult({
        status: 'error',
        errors: ['WebSocket connection error'],
        logs: logsRef.current
      });
      setExecuting(false);
    });

    // Handle connection open
    const unsubscribeOpen = wsService.on('open', () => {
      // Convert React Flow format to workflow format
      const workflow = {
        name: 'Interactive Workflow',
        nodes: nodes.map((node) => ({
          id: node.id,
          type: 'mcp_call',
          mcp_server: node.data.mcp_server,
          tool: node.data.tool,
          params: node.data.params || {},
        })),
        edges: edges.map((edge) => ({
          source: edge.source,
          target: edge.target,
        })),
      };

      // Send workflow to execute
      wsService.send({ workflow });
    });

    // Connect
    wsService.connect(`/ws/execute/${sessionId}`);

    // Return cleanup function
    return () => {
      unsubscribeMessage();
      unsubscribeError();
      unsubscribeOpen();
      wsService.close();
    };
  }, []);

  const handleMessage = useCallback((message, onNodeStateUpdate) => {
    if (message.type === 'log') {
      // Add log to list
      logsRef.current.push(message.log);

      // Update result with current logs
      setResult({
        status: 'running',
        results: {},
        errors: [],
        logs: [...logsRef.current],
        node_states: message.node_states || {}
      });
    } else if (message.type === 'node_state') {
      // Update specific node state in real-time
      if (onNodeStateUpdate) {
        onNodeStateUpdate(message.node_id, message.status, message.node_states);
      }
    } else if (message.type === 'complete') {
      // Execution complete
      console.log('Execution complete, result:', message.result);

      // Log each result for debugging
      if (message.result?.results) {
        Object.entries(message.result.results).forEach(([nodeId, data]) => {
          console.log(`Result for ${nodeId}:`, typeof data, data);
        });
      }

      setResult(message.result);
      setExecuting(false);

      // Final node state update
      if (onNodeStateUpdate && message.result?.node_states) {
        Object.entries(message.result.node_states).forEach(([nodeId, status]) => {
          onNodeStateUpdate(nodeId, status, message.result.node_states);
        });
      }

      // Close connection
      if (wsServiceRef.current) {
        wsServiceRef.current.close();
      }
    } else if (message.type === 'error') {
      // Error occurred
      console.error('Execution error:', message.error);
      setResult({
        status: 'error',
        results: {},
        errors: [message.error],
        logs: logsRef.current,
        node_states: {}
      });
      setExecuting(false);

      // Close connection
      if (wsServiceRef.current) {
        wsServiceRef.current.close();
      }
    }
  }, []);

  return {
    executing,
    result,
    executeWorkflow,
  };
}

export default useExecution;
