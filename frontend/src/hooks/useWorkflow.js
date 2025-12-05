/*
 * Copyright (c) 2025 adcl.io
 * All Rights Reserved.
 *
 * This software is proprietary and confidential. Unauthorized copying,
 * distribution, or use of this software is strictly prohibited.
 */

import { useCallback } from 'react';
import { useNodesState, useEdgesState, addEdge } from 'reactflow';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Custom hook for workflow state management
 * Manages nodes, edges, and workflow operations
 */
function useWorkflow() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Handle edge connections
  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  // Reset all nodes to idle state
  const resetNodeStates = useCallback(() => {
    setNodes((nds) =>
      nds.map((node) => ({
        ...node,
        data: { ...node.data, executionStatus: 'idle' },
      }))
    );
  }, [setNodes]);

  // Update specific node execution state
  const updateNodeState = useCallback((nodeId, status, allNodeStates) => {
    setNodes((nds) => {
      // If we have all node states, update all at once
      if (allNodeStates) {
        return nds.map((node) => ({
          ...node,
          data: {
            ...node.data,
            executionStatus: allNodeStates[node.id] || node.data.executionStatus,
          },
        }));
      }

      // Otherwise just update the specific node
      return nds.map((node) =>
        node.id === nodeId
          ? {
              ...node,
              data: {
                ...node.data,
                executionStatus: status,
              },
            }
          : node
      );
    });
  }, [setNodes]);

  // Load example workflow from backend
  const loadExampleWorkflow = useCallback(async (filename = 'hello_world.json') => {
    try {
      const response = await axios.get(`${API_URL}/workflows/examples/${filename}`);
      const workflow = response.data;

      // Convert workflow to React Flow format
      const flowNodes = workflow.nodes.map((node, index) => ({
        id: node.id,
        type: 'mcpNode',
        position: { x: 100 + index * 250, y: 100 },
        data: {
          label: `${node.mcp_server}.${node.tool}`,
          mcp_server: node.mcp_server,
          tool: node.tool,
          params: node.params,
        },
      }));

      const flowEdges = workflow.edges.map((edge, index) => ({
        id: `edge-${index}`,
        source: edge.source,
        target: edge.target,
        sourceHandle: 'output',
        targetHandle: 'input',
        animated: true,
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (error) {
      console.error('Failed to load example workflow:', error);
      throw error;
    }
  }, [setNodes, setEdges]);

  // Add a new node to the workflow
  const addNode = useCallback((mcpServer, tool, position = null) => {
    const newNode = {
      id: `node-${Date.now()}`,
      type: 'mcpNode',
      position: position || { x: Math.random() * 400, y: Math.random() * 400 },
      data: {
        label: `${mcpServer}.${tool}`,
        mcp_server: mcpServer,
        tool: tool,
        params: {},
      },
    };

    setNodes((nds) => [...nds, newNode]);
    return newNode.id;
  }, [setNodes]);

  // Remove a node from the workflow
  const removeNode = useCallback((nodeId) => {
    setNodes((nds) => nds.filter((node) => node.id !== nodeId));
    setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
  }, [setNodes, setEdges]);

  // Update node parameters
  const updateNodeParams = useCallback((nodeId, params) => {
    setNodes((nds) =>
      nds.map((node) =>
        node.id === nodeId
          ? {
              ...node,
              data: {
                ...node.data,
                params: params,
              },
            }
          : node
      )
    );
  }, [setNodes]);

  // Clear workflow
  const clearWorkflow = useCallback(() => {
    setNodes([]);
    setEdges([]);
  }, [setNodes, setEdges]);

  // Save workflow to backend
  const saveWorkflow = useCallback(async (name, description = '') => {
    const workflow = {
      name,
      description,
      nodes: nodes.map(node => ({
        id: node.id,
        type: 'mcp_call',
        mcp_server: node.data.mcp_server,
        tool: node.data.tool,
        params: node.data.params || {},
      })),
      edges: edges.map(edge => ({
        source: edge.source,
        target: edge.target,
      })),
    };

    const response = await axios.post(`${API_URL}/workflows`, workflow);
    return response.data;
  }, [nodes, edges]);

  // Load workflow from backend
  const loadWorkflow = useCallback(async (filename) => {
    const response = await axios.get(`${API_URL}/workflows/${filename}`);
    const workflow = response.data;

    const flowNodes = workflow.nodes.map((node, index) => ({
      id: node.id,
      type: 'mcpNode',
      position: { x: 100 + index * 250, y: 100 },
      data: {
        label: `${node.mcp_server}.${node.tool}`,
        mcp_server: node.mcp_server,
        tool: node.tool,
        params: node.params,
      },
    }));

    const flowEdges = workflow.edges.map((edge, index) => ({
      id: `edge-${index}`,
      source: edge.source,
      target: edge.target,
      sourceHandle: 'output',
      targetHandle: 'input',
      animated: true,
    }));

    setNodes(flowNodes);
    setEdges(flowEdges);
    return workflow;
  }, [setNodes, setEdges]);

  // List all saved workflows
  const listWorkflows = useCallback(async () => {
    const response = await axios.get(`${API_URL}/workflows`);
    return response.data;
  }, []);

  // Delete workflow
  const deleteWorkflow = useCallback(async (filename) => {
    await axios.delete(`${API_URL}/workflows/${filename}`);
  }, []);

  return {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    resetNodeStates,
    updateNodeState,
    loadExampleWorkflow,
    addNode,
    removeNode,
    updateNodeParams,
    clearWorkflow,
    saveWorkflow,
    loadWorkflow,
    listWorkflows,
    deleteWorkflow,
  };
}

export default useWorkflow;
